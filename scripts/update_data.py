from __future__ import annotations
import os
import json
import sys
from pathlib import Path
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.dart_client import DartClient
from src.normalize import REPORT_NAMES, transform
from src.legacy import extract_legacy

CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
client = DartClient(os.environ.get("DART_API_KEY"))
corp = CFG["company"]["corp_code"]
start = int(CFG["company"]["start_year"])
end = pd.Timestamp.now().year
account_map = CFG["financial_accounts"]

(ROOT / "data/raw").mkdir(parents=True, exist_ok=True)
(ROOT / "data/processed").mkdir(parents=True, exist_ok=True)

rows = []
report_rows = []

for year in range(start, end + 1):
    # One report-list request per year. This is also used to record DART receipt links.
    reports = client.reports(corp, f"{year}0101", f"{year}1231")
    for r in reports:
        name = r.get("report_nm", "")
        if any(x in name for x in ("사업보고서", "반기보고서", "분기보고서")) and "정정" not in name:
            report_rows.append(r)

    for code, label in REPORT_NAMES.items():
        try:
            if year >= 2015:
                accounts = client.financial_statements(corp, year, code, CFG["company"]["fs_div"])
                if not accounts:
                    accounts = client.financial_statements(corp, year, code, "OFS")
                if accounts:
                    target_name = {"11011":"사업보고서", "11012":"반기보고서", "11013":"1분기보고서", "11014":"3분기보고서"}[code]
                    matching = [x for x in reports if target_name in x.get("report_nm", "") and "정정" not in x.get("report_nm", "")]
                    rcp = matching[-1].get("rcept_no") if matching else None
                    rows.append({"year": year, "report_type": label, "reprt_code": code,
                                 "accounts": accounts, "rcept_no": rcp})
            else:
                target = {"11011":"사업보고서", "11012":"반기보고서", "11013":"분기보고서", "11014":"분기보고서"}[code]
                candidates = [x for x in reports if target in x.get("report_nm", "") and "정정" not in x.get("report_nm", "")]
                if code == "11013":
                    candidates = [x for x in candidates if "1분기" in x.get("report_nm", "")]
                elif code == "11014":
                    candidates = [x for x in candidates if "3분기" in x.get("report_nm", "")]
                if candidates:
                    doc = candidates[-1]
                    txt = client.unzip_text(client.download_document(doc["rcept_no"]))
                    vals = extract_legacy(txt, account_map)
                    accounts = [{"account_nm": k, "thstrm_amount": v} for k, v in vals.items() if v is not None]
                    rows.append({"year": year, "report_type": label, "reprt_code": code,
                                 "accounts": accounts, "rcept_no": doc["rcept_no"]})
        except Exception as exc:
            print(f"WARN {year} {code}: {exc}", file=sys.stderr)

raw = pd.DataFrame(report_rows)
if not raw.empty:
    raw["dart_url"] = raw["rcept_no"].map(lambda x: f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={x}")
raw.to_csv(ROOT / "data/raw/reports.csv", index=False, encoding="utf-8-sig")

out = transform(rows, account_map)
if not out.empty:
    out = out.drop_duplicates(["year", "reprt_code"], keep="last").sort_values(["year", "reprt_code"])
out.to_csv(ROOT / "data/processed/financials.csv", index=False, encoding="utf-8-sig")
meta = {
    "company": CFG["company"],
    "updated_at": pd.Timestamp.utcnow().isoformat(),
    "rows": int(len(out)),
    "note": "OpenDART structured financial APIs provide data from 2015 onward; 2010-2014 uses original periodic-report fallback parsing."
}
(ROOT / "data/processed/metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved {len(out)} financial observations and {len(raw)} report records.")
