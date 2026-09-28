# SK이노베이션 DART Financial Agent

<p align="center"><a href="https://hsc-class01.github.io/JY_SKinno/"><img src="https://img.shields.io/badge/%F0%9F%94%97%20%EB%8C%80%EC%8B%9C%EB%B3%B4%EB%93%9C%20%EB%B0%94%EB%A1%9C%EA%B0%80%EA%B8%B0-2F80ED?style=for-the-badge&logo=github&logoColor=white" alt="대시보드 바로가기"></a></p>

DART OpenAPI를 이용해 SK이노베이션의 정기보고서 재무 데이터를 수집하고, 주요 재무수치와 재무비율을 계산한 뒤 GitHub Pages 대시보드로 공개하는 자동화 프로젝트입니다.

## Dashboard

**[🔗 대시보드 바로가기](https://hsc-class01.github.io/JY_SKinno/)**

## 자동화 범위

- 대상: SK이노베이션 (`corp_code=00126380`, `stock_code=096770`)
- 시작연도: 2010
- 보고서: 사업보고서, 반기보고서, 1분기보고서, 3분기보고서
- 자동화: 매월 1일 GitHub Actions 실행
- 데이터: DART OpenAPI → CSV → 정적 Plotly dashboard
- 배포: GitHub Pages
- API key: GitHub Actions Secret `DART_API_KEY`에만 저장

> OpenDART의 구조화된 재무제표 API는 2015년 이후 데이터를 제공하므로 2010~2014년은 DART 공시검색 + 공시서류원본파일 API를 이용한 보완 파싱 경로를 사용합니다. 원문 전체를 저장하기보다 공시 메타데이터와 추출 수치를 저장하도록 설계했습니다.

## 주요 재무수치

기본 설정에는 매출액, 영업이익, 당기순이익, 자산총계, 부채총계, 자본총계, 유동자산, 유동부채, 현금및현금성자산, 영업활동현금흐름, 유형자산 취득 등을 포함합니다. `config.yaml`에서 계정명을 추가/수정할 수 있습니다.

## 주요 재무비율

- 영업이익률
- 순이익률
- 유동비율
- 부채비율
- 자기자본비율
- ROA
- ROE
- 총자산회전율
- 부채비율(자산기준)

## 국내 Peer Firms

| 기업 | 사업영역 | 상장여부 | 주요 비교영역 |
|---|---|---|---|
| S-OIL | 정유/석유화학 | 상장 | 정유 및 석유화학 |
| GS칼텍스 | 정유/석유화학 | 비상장 | 정유 및 석유화학 |
| HD현대오일뱅크 | 정유/석유화학 | 비상장 | 정유 및 석유화학 |
| LG에너지솔루션 | 배터리 | 상장 | 전기차·ESS 배터리 |
| 삼성SDI | 배터리/소재 | 상장 | 배터리·전자재료 |
| LG화학 | 화학/배터리 소재 | 상장 | 석유화학·첨단소재·배터리 소재 |

Peer set은 SK이노베이션의 복합 사업구조를 고려한 **사업영역별 비교군**이며, 우열이나 투자등급을 의미하지 않습니다.

## GitHub Pages 최초 설정

1. Repository → **Settings → Pages**
2. **Build and deployment → Source: GitHub Actions** 선택
3. Actions에서 `DART update and GitHub Pages`를 `Run workflow`로 한 번 실행
4. 정상 배포 후 `https://hsc-class01.github.io/JY_SKinno/`에서 확인
5. Repository 메인 페이지의 **About → Website**에 같은 Dashboard URL을 입력하면 오른쪽 About에 링크가 표시됩니다.

## DART API Key 설정

1. OpenDART에서 API 인증키를 발급합니다.
2. GitHub Repository → **Settings → Secrets and variables → Actions**
3. **New repository secret**
4. Name: `DART_API_KEY`
5. Secret: 발급받은 40자리 인증키
6. 저장 후 Actions에서 workflow를 수동 실행합니다.

API key는 코드, README, CSV, dashboard에 넣지 마십시오.

## 파일 구조

```text
JY_SKinno/
├─ .github/workflows/update-and-deploy.yml
├─ data/raw/reports.csv
├─ data/processed/financials.csv
├─ data/processed/metadata.json
├─ docs/index.html
├─ scripts/update_data.py
├─ scripts/build_dashboard.py
├─ src/dart_client.py
├─ src/legacy.py
├─ src/normalize.py
├─ config.yaml
├─ requirements.txt
└─ README.md
```
