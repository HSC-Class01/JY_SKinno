from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
META_PATH = ROOT / "data/processed/metadata.json"
DATA_PATH = ROOT / "data/processed/financials.csv"

if not META_PATH.exists() or not DATA_PATH.exists():
    raise RuntimeError("Financial data or metadata is missing. Run update_data.py first.")

meta = json.loads(META_PATH.read_text(encoding="utf-8"))
company = meta.get("company", {})
expected_corp = str(CFG["company"]["corp_code"]).zfill(8)
expected_stock = str(CFG["company"]["stock_code"]).zfill(6)

if str(company.get("corp_code", "")).zfill(8) != expected_corp:
    raise RuntimeError("Metadata corp_code does not match config.yaml.")
if str(company.get("stock_code", "")).zfill(6) != expected_stock:
    raise RuntimeError("Metadata stock_code does not match config.yaml.")

df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
if df.empty or "revenue" not in df or df["revenue"].notna().sum() == 0:
    raise RuntimeError("No valid revenue observations are available for the dashboard.")

df["year"] = pd.to_numeric(df["year"], errors="coerce")
df = df.dropna(subset=["year"]).copy()
df["year"] = df["year"].astype(int)
period_order = {
    "quarterly_q1": 1,
    "half_year": 2,
    "quarterly_q3": 3,
    "annual": 4,
}
df["_period_order"] = df["report_type"].map(period_order).fillna(0)
df = df.sort_values(["year", "_period_order"]).drop(columns="_period_order")

# Convert NumPy values and missing observations into strict JSON values.
records = []
for raw_record in df.to_dict(orient="records"):
    record = {}
    for key, value in raw_record.items():
        if pd.isna(value):
            record[key] = None
        elif hasattr(value, "item"):
            record[key] = value.item()
        else:
            record[key] = value
    records.append(record)

payload = json.dumps(records, ensure_ascii=False, allow_nan=False)
peers = [
    ("S-OIL", "정유/석유화학", "상장", "정유 및 석유화학"),
    ("GS칼텍스", "정유/석유화학", "비상장", "정유 및 석유화학"),
    ("HD현대오일뱅크", "정유/석유화학", "비상장", "정유 및 석유화학"),
    ("LG에너지솔루션", "배터리", "상장", "전기차·ESS 배터리"),
    ("삼성SDI", "배터리/소재", "상장", "배터리·전자재료"),
    ("LG화학", "화학/배터리 소재", "상장", "석유화학·첨단소재·배터리 소재"),
]
peer_html = "".join(
    f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>"
    for a, b, c, d in peers
)

html = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SK이노베이션 Financial Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{color-scheme:light}
*{box-sizing:border-box}
body{font-family:Inter,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f6f8fb;color:#172033;margin:0}
.wrap{width:min(100% - 32px,1400px);margin:auto;padding:28px 0 70px}
header{background:#111827;color:white;border-radius:20px;padding:28px 30px;margin-bottom:22px}
h1{margin:0 0 8px;font-size:30px}.sub{opacity:.82;line-height:1.6}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:18px 0}
.card{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px;box-shadow:0 4px 18px rgba(17,24,39,.05);min-width:0}
.label{font-size:12px;color:#6b7280}.value{font-size:clamp(19px,2.2vw,25px);font-weight:700;margin-top:7px;overflow-wrap:anywhere}
.section{margin-top:24px;min-width:0}h2{font-size:20px;margin:0 0 12px}
.chart{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:8px;margin:14px 0;min-width:0;overflow:hidden}
.chart>div{width:100%!important;min-width:0}
.tablewrap{width:100%;overflow-x:auto;overflow-y:hidden;-webkit-overflow-scrolling:touch;background:white;border:1px solid #e5e7eb;border-radius:14px}
table{width:100%;min-width:1180px;border-collapse:collapse;background:white}
th,td{padding:10px 12px;border-bottom:1px solid #edf0f4;text-align:right;white-space:nowrap;font-size:13px}
th{background:#f1f5f9;color:#475569;font-size:12px;position:sticky;top:0}
th:first-child,td:first-child{text-align:left}
td a{color:#2563eb;text-decoration:none}td a:hover{text-decoration:underline}
.note{font-size:12px;color:#64748b;line-height:1.7}
.status{font-size:12px;color:#64748b;margin:8px 2px}
@media(max-width:900px){.wrap{width:min(100% - 20px,1400px);padding-top:16px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:24px}.chart{padding:4px}}
@media(max-width:600px){.grid{grid-template-columns:1fr}header{padding:22px}.section{margin-top:20px}h2{font-size:18px}.chart{border-radius:12px}}
</style>
</head>
<body>
<div class="wrap">
<header>
<h1>SK이노베이션 Financial Dashboard</h1>
<div class="sub">DART OpenAPI 기반 · 재무 데이터 2015–현재 · 보고서 목록 2010–현재</div>
<div class="sub">종목코드 096770 · 재무 금액 단위: 억 원</div>
</header>
<div class="grid" id="cards"></div>
<div class="section"><h2>Financial Trend</h2><div class="chart" id="trend"></div><div class="status">연간 재무수치 · 금액 단위: 억 원</div></div>
<div class="section"><h2>Profitability & Stability</h2><div class="chart" id="ratios"></div><div class="status">비율 지표 · 단위: %</div></div>
<div class="section"><h2>Annual</h2><div class="tablewrap" id="annual"></div></div>
<div class="section"><h2>Half-year</h2><div class="tablewrap" id="half"></div></div>
<div class="section"><h2>Quarterly</h2><div class="tablewrap" id="quarter"></div></div>
<div class="section">
<h2>Domestic Peer Firms</h2>
<div class="tablewrap"><table style="min-width:720px"><thead><tr><th>기업</th><th>사업영역</th><th>상장여부</th><th>주요 비교영역</th></tr></thead><tbody>__PEERS__</tbody></table></div>
<p class="note">Peer set은 SK이노베이션의 복합 사업구조를 고려한 국내 사업영역별 비교군이며, 우열 또는 투자등급을 의미하지 않습니다.</p>
</div>
<p class="note">Source: Financial Supervisory Service OpenDART. 결측 계정은 임의로 0으로 대체하지 않습니다. 비율은 수집된 원시 재무제표 계정으로 계산합니다. 분기별 계정의 기간 누적/당기 구분은 DART 원문 공시와 대조해 사용하십시오.</p>
<p class="note">Data last updated: __UPDATED__ · Published observations: __ROWS__</p>
</div>
<script>
const DATA=__DATA__;
const amountKeys=new Set(["revenue","operating_profit","net_income","assets","liabilities","equity","current_assets","current_liabilities","cash","borrowings","operating_cash_flow","capex"]);
const ratioKeys=new Set(["operating_margin","net_margin","current_ratio","debt_to_equity","equity_ratio","roa","roe","debt_ratio"]);
const multipleKeys=new Set(["asset_turnover"]);
const cols=["year","report_type","revenue","operating_profit","net_income","assets","liabilities","equity","current_assets","current_liabilities","cash","borrowings","operating_cash_flow","capex","operating_margin","net_margin","current_ratio","debt_to_equity","equity_ratio","asset_turnover","roa","roe","debt_ratio","rcept_no"];
const names={year:"연도",report_type:"보고서",revenue:"매출액",operating_profit:"영업이익",net_income:"당기순이익",assets:"자산총계",liabilities:"부채총계",equity:"자본총계",current_assets:"유동자산",current_liabilities:"유동부채",cash:"현금및현금성자산",borrowings:"차입금",operating_cash_flow:"영업활동현금흐름",capex:"유형자산 취득",operating_margin:"영업이익률",net_margin:"순이익률",current_ratio:"유동비율",debt_to_equity:"부채/자본",equity_ratio:"자기자본비율",asset_turnover:"총자산회전율",roa:"ROA",roe:"ROE",debt_ratio:"부채/자산",rcept_no:"DART 원문"};
const reportNames={annual:"사업보고서",half_year:"반기보고서",quarterly_q1:"1분기",quarterly_q3:"3분기"};
const fmt=(x,d=2)=>x==null||!Number.isFinite(Number(x))?"—":Number(x).toLocaleString("ko-KR",{maximumFractionDigits:d});
const won=(x)=>x==null?"—":fmt(Number(x)/100000000,1);
const pct=(x)=>x==null?"—":fmt(Number(x)*100,2)+"%";
const ordered=[...DATA].sort((a,b)=>a.year-b.year);
const latest=ordered.length?ordered[ordered.length-1]:{};
document.getElementById("cards").innerHTML=[
 ["최근 보고기간",(latest.year?latest.year+"년 ":"")+(reportNames[latest.report_type]||"—")],
 ["매출액",latest.revenue==null?"—":won(latest.revenue)+" 억 원"],
 ["영업이익",latest.operating_profit==null?"—":won(latest.operating_profit)+" 억 원"],
 ["당기순이익",latest.net_income==null?"—":won(latest.net_income)+" 억 원"]
].map(([label,value])=>'<div class="card"><div class="label">'+label+'</div><div class="value">'+value+'</div></div>').join("");
function renderTable(id,arr){
 const target=document.getElementById(id);
 if(!arr.length){target.innerHTML='<p class="note">데이터 없음</p>';return;}
 const keys=cols.filter(k=>arr.some(r=>r[k]!=null));
 let html='<table><thead><tr>'+keys.map(k=>'<th>'+names[k]+'</th>').join("")+'</tr></thead><tbody>';
 for(const row of arr){
  html+='<tr>'+keys.map(k=>{
   if(k==="report_type") return '<td>'+ (reportNames[row[k]]||row[k])+'</td>';
   if(k==="rcept_no") return '<td>'+(row[k]?'<a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+encodeURIComponent(row[k])+'" target="_blank" rel="noopener">원문 보기</a>':"—")+'</td>';
   if(amountKeys.has(k)) return '<td>'+won(row[k])+'</td>';
   if(multipleKeys.has(k)) return '<td>'+fmt(row[k],2)+'x</td>';
   if(ratioKeys.has(k)) return '<td>'+pct(row[k])+'</td>';
   return '<td>'+fmt(row[k],0)+'</td>';
  }).join("")+'</tr>';
 }
 html+='</tbody></table>';
 target.innerHTML=html;
}
const annual=ordered.filter(r=>r.report_type==="annual");
const half=ordered.filter(r=>r.report_type==="half_year");
const quarter=ordered.filter(r=>String(r.report_type||"").startsWith("quarterly"));
renderTable("annual",annual);
renderTable("half",half);
renderTable("quarter",quarter);
const years=annual.map(r=>r.year);
const by=key=>annual.map(r=>r[key]==null?null:Number(r[key])/100000000);
const ratioBy=key=>annual.map(r=>r[key]==null?null:Number(r[key])*100);
const layout={autosize:true,height:430,margin:{t:22,r:24,l:78,b:80},legend:{orientation:"h",x:0,y:-0.22,xanchor:"left",yanchor:"top"},hovermode:"x unified",paper_bgcolor:"white",plot_bgcolor:"white",font:{family:"Inter,system-ui,sans-serif",size:12}};
if(window.Plotly){
 Plotly.newPlot("trend",[
  {x:years,y:by("revenue"),name:"매출액",type:"scatter",mode:"lines+markers"},
  {x:years,y:by("operating_profit"),name:"영업이익",type:"scatter",mode:"lines+markers"},
  {x:years,y:by("net_income"),name:"당기순이익",type:"scatter",mode:"lines+markers"}
 ],{...layout,yaxis:{title:"억 원",automargin:true,tickformat:",.0f"}},{responsive:true,displaylogo:false});
 Plotly.newPlot("ratios",[
  {x:years,y:ratioBy("operating_margin"),name:"영업이익률",type:"scatter",mode:"lines+markers"},
  {x:years,y:ratioBy("net_margin"),name:"순이익률",type:"scatter",mode:"lines+markers"},
  {x:years,y:ratioBy("equity_ratio"),name:"자기자본비율",type:"scatter",mode:"lines+markers"},
  {x:years,y:ratioBy("roa"),name:"ROA",type:"scatter",mode:"lines+markers"},
  {x:years,y:ratioBy("roe"),name:"ROE",type:"scatter",mode:"lines+markers"}
 ],{...layout,yaxis:{title:"%",automargin:true,ticksuffix:"%"}},{responsive:true,displaylogo:false});
 window.addEventListener("resize",()=>{
  const trend=document.getElementById("trend"),ratios=document.getElementById("ratios");
  if(trend.data) Plotly.Plots.resize(trend);
  if(ratios.data) Plotly.Plots.resize(ratios);
 });
}else{
 document.getElementById("trend").innerHTML='<p class="note">차트 라이브러리를 불러오지 못했습니다. 표 데이터를 확인해 주세요.</p>';
 document.getElementById("ratios").innerHTML='<p class="note">차트 라이브러리를 불러오지 못했습니다. 표 데이터를 확인해 주세요.</p>';
}
</script>
</body>
</html>
"""
html = (
    html.replace("__DATA__", payload)
    .replace("__PEERS__", peer_html)
    .replace("__UPDATED__", str(meta.get("updated_at", "unknown")))
    .replace("__ROWS__", str(len(df)))
)
(ROOT / "docs" / "index.html").write_text(html, encoding="utf-8")
print(f"Built dashboard with {len(df)} observations for {CFG['company']['name']}.")
