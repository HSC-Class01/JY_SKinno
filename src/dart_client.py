from __future__ import annotations
import io
import zipfile
import requests


BASE = "https://opendart.fss.or.kr/api"


class DartError(RuntimeError):
    def __init__(self, message: str, status: str | None = None):
        super().__init__(message)
        self.status = status


class DartClient:
    def __init__(self, api_key: str | None):
        if not api_key:
            raise DartError("DART_API_KEY is not set")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "JY_SKinno-DART-Agent/2.0"})

    def get_json(self, endpoint: str, params: dict) -> dict:
        query = dict(params)
        query["crtfc_key"] = self.api_key
        response = self.session.get(
            f"{BASE}/{endpoint}.json", params=query, timeout=60
        )
        response.raise_for_status()
        data = response.json()
        status = str(data.get("status", ""))
        # DART 013 means there is no filing for the requested period.
        if status == "013":
            return {**data, "list": []}
        if status != "000":
            raise DartError(
                f"DART {status}: {data.get('message', 'Unknown API error')}",
                status=status,
            )
        return data

    def company(self, corp_code: str) -> dict:
        return self.get_json("company", {"corp_code": corp_code})

    def reports(
        self, corp_code: str, start: str, end: str, page_count: int = 100
    ) -> list[dict]:
        results = []
        page = 1
        while True:
            data = self.get_json("list", {
                "corp_code": corp_code,
                "bgn_de": start,
                "end_de": end,
                "page_no": page,
                "page_count": page_count,
                "sort": "date",
                "sort_mth": "asc",
            })
            results.extend(data.get("list", []))
            if page >= int(data.get("total_page", 1)):
                return results
            page += 1

    def financial_statements(
        self, corp_code: str, year: int, reprt_code: str, fs_div: str = "CFS"
    ) -> list[dict]:
        data = self.get_json("fnlttSinglAcntAll", {
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
            "fs_div": fs_div,
        })
        return data.get("list", [])

    def download_document(self, rcept_no: str) -> bytes:
        response = self.session.get(
            f"{BASE}/document.xml",
            params={"crtfc_key": self.api_key, "rcept_no": rcept_no},
            timeout=120,
        )
        response.raise_for_status()
        if not response.content.startswith(b"PK"):
            raise DartError(
                f"DART document.xml did not return a ZIP archive: {rcept_no}"
            )
        return response.content

    @staticmethod
    def unzip_text(blob: bytes) -> str:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            parts = []
            for name in archive.namelist():
                raw = archive.read(name)
                decoded = None
                for encoding in ("utf-8", "euc-kr", "cp949"):
                    try:
                        decoded = raw.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                parts.append(
                    decoded if decoded is not None
                    else raw.decode("utf-8", errors="ignore")
                )
            return "\n".join(parts)
