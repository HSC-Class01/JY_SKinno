from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.dart_client import DartClient, DartError
from src.normalize import REPORT_NAMES, transform
from src.legacy import extract_legacy


CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
COMPANY = CFG["company"]
CORP_CODE = str(COMPANY["corp_code"]).zfill(8)
STOCK_CODE = str(COMPANY["stock_code"]).zfill(6)
START_YEAR = int(COMPANY["start_year"])
END_YEAR = pd.Timestamp.now().year

for output_dir in (
    ROOT / "data/raw",
    ROOT / "data/processed",
    ROOT / "docs",
):
    output_dir.mkdir(parents=True, exist_ok=True)

client = DartClient(os.environ.get("DART_API_KEY"))

# Verify the issuer using DART company profile. If that endpoint alone is
# temporarily unavailable, the periodic-report search below provides a second
# official DART identity check before any output file is written.
profile = None
try:
    profile = client.company(CORP_CODE)
except DartError as exc:
    print(
        f"WARN: DART company profile unavailable; "
        f"will verify against official filing metadata: {exc}",
        file=sys.stderr,
    )

# Search a filing window wide enough to include the next-year annual report.
today = pd.Timestamp.now().normalize()
report_end = (today + pd.Timedelta(days=120)).strftime("%Y%m%d")
all_reports = client.reports(
    CORP_CODE, f"{START_YEAR}0101", report_end, pblntf_ty="A"
)

identity_records = [
    report for report in all_reports
    if str(report.get("corp_code", "")).zfill(8) == CORP_CODE
]
if profile is not None:
    actual_stock_code = str(profile.get("stock_code", "")).zfill(6)
    actual_name = str(profile.get("corp_name", ""))
    if actual_stock_code != STOCK_CODE:
        raise RuntimeError(
            "DART company identity mismatch: "
            f"configured={COMPANY['name']} ({STOCK_CODE}/{CORP_CODE}), "
            f"API={actual_name} ({actual_stock_code}/{CORP_CODE}). "
            "No output files were overwritten."
        )
else:
    # A failed company-profile request must not silently disable validation.
    # Require the independently returned DART filing records to identify the
    # exact stock code and the expected issuer name.
    observed_stock_codes = {
        str(report.get("stock_code") or "").strip().zfill(6)
        for report in identity_records
        if str(report.get("stock_code") or "").strip()
    }
    observed_names = {
        str(report.get("corp_name") or "").strip()
        for report in identity_records
        if str(report.get("corp_name") or "").strip()
    }
    if (
        STOCK_CODE not in observed_stock_codes
        or not observed_names
        or not all(
            ("SK이노베이션" in name or "SK Innovation" in name)
            for name in observed_names
        )
    ):
        raise RuntimeError(
            "DART issuer could not be verified from filing metadata: "
            f"corp_code={CORP_CODE}, stock_codes={sorted(observed_stock_codes)}, "
            f"names={sorted(observed_names)}. "
            "No output files were overwritten."
        )
    actual_stock_code = STOCK_CODE
    actual_name = sorted(observed_names)[0]

# Keep only this issuer's periodic reports and verify the issuer on each row.
periodic_reports = []
for report in all_reports:
    report_corp = str(report.get("corp_code", "")).zfill(8)
    report_stock = str(report.get("stock_code") or "").strip()
    report_stock = report_stock.zfill(6) if report_stock else ""
    report_name = str(report.get("report_nm", ""))
    if report_corp != CORP_CODE or report_stock not in ("", STOCK_CODE):
        continue
    if not any(term in report_name for term in (
        "사업보고서", "반기보고서", "분기보고서"
    )):
        continue
    if "정정" in report_name:
        continue
    periodic_reports.append(report)

def find_periodic_report(year: int, code: str):
    month = {
        "11011": "12",
        "11012": "06",
        "11013": "03",
        "11014": "09",
    }[code]
    period = f"({year}.{month})"
    keyword = "사업보고서" if code == "11011" else (
        "반기보고서" if code == "11012" else "분기보고서"
    )
    candidates = [
        report for report in periodic_reports
        if keyword in str(report.get("report_nm", ""))
        and period in str(report.get("report_nm", ""))
    ]
    return candidates[-1] if candidates else None


rows = []
report_rows = []
for report in periodic_reports:
    item = dict(report)
    item["dart_url"] = (
        "https://dart.fss.or.kr/dsaf001/main.do?rcpNo="
        + str(report.get("rcept_no", ""))
    )
    report_rows.append(item)

for year in range(START_YEAR, END_YEAR + 1):
    for code, label in REPORT_NAMES.items():
        report = find_periodic_report(year, code)
        try:
            if year >= 2015:
                accounts = client.financial_statements(
                    CORP_CODE, year, code, COMPANY.get("fs_div", "CFS")
                )
                if not accounts and COMPANY.get("fs_div", "CFS") == "CFS":
                    accounts = client.financial_statements(
                        CORP_CODE, year, code, "OFS"
                    )
                if accounts:
                    rcept_no = (
                        accounts[0].get("rcept_no")
                        or (report or {}).get("rcept_no")
                    )
                    rows.append({
                        "year": year,
                        "report_type": label,
                        "reprt_code": code,
                        "accounts": accounts,
                        "rcept_no": str(rcept_no) if rcept_no else None,
                    })
            elif report:
                # DART structured statements are not available for these early years.
                # Keep an observation only when the original filing yields actual values.
                rcept_no = str(report["rcept_no"])
                document = client.unzip_text(client.download_document(rcept_no))
                values = extract_legacy(document, CFG["financial_accounts"])
                # extract_legacy returns normalized field keys, whereas transform()
                # resolves DART account labels. Map each value back to its first
                # configured Korean account label before running the common pipeline.
                core_fields = (
                    "revenue", "operating_profit", "net_income",
                    "assets", "liabilities", "equity",
                )
                if any(values.get(key) is not None for key in core_fields):
                    accounts = [
                        {
                            "account_nm": CFG["financial_accounts"][key][0],
                            "thstrm_amount": value,
                        }
                        for key, value in values.items()
                        if value is not None and CFG["financial_accounts"].get(key)
                    ]
                    rows.append({
                        "year": year,
                        "report_type": label,
                        "reprt_code": code,
                        "accounts": accounts,
                        "rcept_no": rcept_no,
                    })
        except Exception as exc:
            print(f"WARN {year} {code}: {exc}", file=sys.stderr)

if not rows:
    raise RuntimeError(
        f"No financial observations were retrieved for {COMPANY['name']}."
    )

# Transform and validate before replacing the currently published dataset.
out = transform(rows, CFG["financial_accounts"])
if out.empty or out["revenue"].notna().sum() == 0:
    raise RuntimeError(
        "No revenue observations were extracted. "
        "The existing published data was left unchanged."
    )

out = out.drop_duplicates(
    ["year", "report_type"], keep="last"
).sort_values(["year", "report_type"]).reset_index(drop=True)

raw = pd.DataFrame(report_rows)
if not raw.empty:
    raw["corp_code"] = raw["corp_code"].astype(str).str.zfill(8)
    raw["stock_code"] = raw["stock_code"].fillna("").astype(str).str.zfill(6)
    if set(raw["corp_code"].dropna()) - {CORP_CODE}:
        raise RuntimeError("Mixed issuer codes detected in reports; export cancelled.")

raw.to_csv(
    ROOT / "data/raw/reports.csv", index=False, encoding="utf-8-sig"
)
out.to_csv(
    ROOT / "data/processed/financials.csv",
    index=False,
    encoding="utf-8-sig",
)
metadata = {
    "company": {
        **COMPANY,
        "corp_code": CORP_CODE,
        "stock_code": STOCK_CODE,
        "verified_corp_name": actual_name,
    },
    "updated_at": pd.Timestamp.now(tz="UTC").isoformat(),
    "rows": int(len(out)),
    "reports": int(len(raw)),
    "revenue_observations": int(out["revenue"].notna().sum()),
    "note": (
        "OpenDART financial statements are used from 2015 onward. "
        "Earlier periods are included only when original-report parsing "
        "returns actual values. Report IDs are taken from the matching "
        "financial statement response or the exact fiscal-period filing."
    ),
}
(ROOT / "data/processed/metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(
    f"Saved {len(out)} financial observations and {len(raw)} periodic reports "
    f"for {actual_name} ({STOCK_CODE}/{CORP_CODE})."
)
