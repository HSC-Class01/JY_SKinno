from __future__ import annotations
import re
from bs4 import BeautifulSoup
from .normalize import num

def extract_legacy(text, account_map):
    soup = BeautifulSoup(text, "lxml")
    clean = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    out = {}
    for key, names in account_map.items():
        value = None
        for name in names:
            # Conservative fallback for 2010-2014 original filings.
            pattern = re.compile(re.escape(name) + r".{0,220}?(-?\(?[0-9][0-9,]*\)?)")
            match = pattern.search(clean)
            if match:
                value = num(match.group(1))
                break
        out[key] = value
    return out
