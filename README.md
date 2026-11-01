# SK이노베이션 DART Financial Agent

DART OpenAPI를 이용해 SK이노베이션의 정기보고서 재무 데이터를 수집하고, 주요 재무수치와 재무비율을 계산한 뒤 GitHub Pages 대시보드로 공개하는 자동화 프로젝트입니다.

## Dashboard

<p align="center">
  <a href="https://hsc-class01.github.io/JY_SKinno/" target="_blank" rel="noopener">
    <img src="https://www.skinnovation.co.kr/resources/images/contents/company/logo-mark.svg" height="46" alt="SK이노베이션 행복날개 심볼" />
    <img src="https://www.skinnovation.co.kr/resources/images/contents/company/logo-txt.svg" height="34" alt="SK이노베이션 워드마크" />
    <br />
    <kbd><strong>FINANCIAL DASHBOARD · 대시보드 바로가기 ↗</strong></kbd>
  </a>
</p>

## 데이터 무결성

DART 기업개황 API로 고유번호와 종목코드(096770)를 먼저 대조합니다. 기업 식별정보가 일치하지 않으면 CSV와 대시보드를 덮어쓰지 않습니다. 재무 CSV와 대시보드 생성 시에도 메타데이터의 기업코드를 재검증합니다.

## 자동화 범위

- 대상: SK이노베이션 (`corp_code=00631518`, `stock_code=096770`)
- 보고서 메타데이터 수집 시작연도: 2010
- 정량 재무데이터 시작연도: 2015
- 보고서: 사업보고서, 반기보고서, 1분기보고서, 3분기보고서
- 자동화: 매월 1일 GitHub Actions 실행
- 데이터: DART OpenAPI → CSV → 정적 Plotly dashboard
- 배포: GitHub Pages
- API key: GitHub Actions Secret `DART_API_KEY`에만 저장

> OpenDART의 구조화된 재무제표 API를 이용한 정량 재무데이터는 2015년 이후부터 제공합니다. 2010~2014년은 DART 보고서 메타데이터와 원문 링크를 보관하지만, 검증되지 않은 텍스트 숫자 추출값이 재무비율을 왜곡할 수 있어 현재 정량 분석에서는 제외합니다. 과거 원문 표를 구조적으로 읽는 검증된 파서를 확보한 뒤 별도로 추가합니다.

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
