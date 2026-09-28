from __future__ import annotations
import io
import zipfile
import requests

BASE = "https://opendart.fss.or.kr/api"

class DartError(RuntimeError):
    pass

class DartClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise DartError("DART_API_KEY is not set")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "JY_SKinno-DART-Agent/1.0"})

    def get_json(self, endpoint: str, params: dict) -> dict:
        q = dict(params)
        q["crtfc_key"] = self.api_key
        r = self.session.get(f"{BASE}/{endpoint}.json", params=q, timeout=60)
        r.raise_for_status()
        data = r.json()
        # 013 means that DART has no matching filing/data. It is normal for
        # some report types and must not stop the monthly job.
        if data.get("status") == "013":
            return {"status": "000", "list": [], "total_page": 1}
        if data.get("status") != "000":
            raise DartError(f"DART {data.get('status')}: {data.get('message')}")
        return data

    def reports(self, corp_code: str, start: str, end: str, page_count: int = 100):
        out, page = [], 1
        while True:
            d = self.get_json("list", {
                "corp_code": corp_code, "bgn_de": start, "end_de": end,
                "page_no": page, "page_count": page_count,
                "sort": "date", "sort_mth": "asc"
            })
            out.extend(d.get("list", []))
            if page >= int(d.get("total_page", 1)):
                return out
            page += 1

    def financial_statements(self, corp_code, year, reprt_code, fs_div="CFS"):
        return self.get_json("fnlttSinglAcntAll", {
            "corp_code": corp_code, "bsns_year": str(year),
            "reprt_code": reprt_code, "fs_div": fs_div
        }).get("list", [])

    def download_document(self, rcept_no: str) -> bytes:
        r = self.session.get(f"{BASE}/document.xml", params={
            "crtfc_key": self.api_key, "rcept_no": rcept_no
        }, timeout=120)
        r.raise_for_status()
        if not r.content.startswith(b"PK"):
            raise DartError(f"DART document.xml did not return ZIP: {rcept_no}")
        return r.content

    @staticmethod
    def unzip_text(blob: bytes) -> str:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            parts = []
            for name in z.namelist():
                raw = z.read(name)
                txt = None
                for enc in ("utf-8", "euc-kr", "cp949"):
                    try:
                        txt = raw.decode(enc)
                        break
                    except UnicodeDecodeError:
                        pass
                parts.append(txt if txt is not None else raw.decode("utf-8", errors="ignore"))
            return "\n".join(parts)
