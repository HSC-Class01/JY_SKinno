from __future__ import annotations
import re
import pandas as pd

REPORT_NAMES = {
    "11011": "annual",
    "11012": "half_year",
    "11013": "quarterly_q1",
    "11014": "quarterly_q3",
}

def num(x):
    if x is None:
        return None
    s = str(x).strip().replace(",", "").replace(" ", "")
    if s in ("", "-", "—", "–", "N/A", "n/a"):
        return None
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    try:
        v = float(s)
        return -v if neg else v
    except ValueError:
        return None

def pick(accounts, names):
    norm = lambda x: re.sub(r"\s+", "", str(x)).lower()
    wanted = [norm(x) for x in names]
    for a in accounts:
        n = norm(a.get("account_nm", ""))
        if n in wanted:
            return num(a.get("thstrm_amount"))
    for a in accounts:
        n = norm(a.get("account_nm", ""))
        if any(w in n for w in wanted):
            return num(a.get("thstrm_amount"))
    return None

def safe_div(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b

def transform(rows, account_map):
    records = []
    for r in rows:
        rec = {
            "year": r["year"], "report_type": r["report_type"],
            "reprt_code": r["reprt_code"], "rcept_no": r.get("rcept_no")
        }
        for key, names in account_map.items():
            rec[key] = pick(r["accounts"], names)
        rec["operating_margin"] = safe_div(rec["operating_profit"], rec["revenue"])
        rec["net_margin"] = safe_div(rec["net_income"], rec["revenue"])
        rec["current_ratio"] = safe_div(rec["current_assets"], rec["current_liabilities"])
        rec["debt_to_equity"] = safe_div(rec["liabilities"], rec["equity"])
        rec["equity_ratio"] = safe_div(rec["equity"], rec["assets"])
        rec["asset_turnover"] = safe_div(rec["revenue"], rec["assets"])
        rec["roa"] = safe_div(rec["net_income"], rec["assets"])
        rec["roe"] = safe_div(rec["net_income"], rec["equity"])
        rec["debt_ratio"] = safe_div(rec["liabilities"], rec["assets"])
        records.append(rec)
    return pd.DataFrame(records)
