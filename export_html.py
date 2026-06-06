"""
Generates a fully self-contained HTML file with all dashboard charts.
Open the output file directly in any browser — no Python/server needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.io as pio
from data.mock_data import (
    get_portfolio_kpis, get_gwp_by_lob, get_gwp_monthly_trend,
    get_loss_ratio_by_lob, get_gwp_by_country, get_large_losses,
    get_dq_trend, get_broker_performance, get_feature_store_summary,
    LOB_COLORS,
)
from datetime import datetime

kpis   = get_portfolio_kpis()
lob    = get_gwp_by_lob()
trend  = get_gwp_monthly_trend(18)
lr     = get_loss_ratio_by_lob()
geo    = get_gwp_by_country()
ll     = get_large_losses(10)
dq     = get_dq_trend(30)
bp     = get_broker_performance()
fs     = get_feature_store_summary()

# ── helpers ──────────────────────────────────────────────────────────────────
def fig_to_div(fig, h=380):
    fig.update_layout(height=h, margin=dict(l=10,r=10,t=40,b=10),
                      paper_bgcolor="white", plot_bgcolor="white",
                      font=dict(family="Inter, sans-serif", size=12))
    return pio.to_html(fig, full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False})

# ── Chart 1: GWP donut ───────────────────────────────────────────────────────
fig1 = px.pie(lob, values="gwp_eur_m", names="lob",
              color="lob", color_discrete_map=LOB_COLORS,
              hole=0.46, title="GWP by Line of Business")
fig1.update_traces(textposition="outside", textinfo="percent+label")
fig1.update_layout(showlegend=False)

# ── Chart 2: Loss ratio bar ──────────────────────────────────────────────────
colors2 = ["#c8102e" if d["status"]=="alert" else "#ed7d31" if d["status"]=="warning" else "#107c10" for d in lr]
fig2 = go.Figure(go.Bar(
    x=[d["lob"] for d in lr], y=[d["loss_ratio"]*100 for d in lr],
    marker_color=colors2, text=[f"{d['loss_ratio']:.1%}" for d in lr],
    textposition="outside",
))
fig2.add_hline(y=70, line_dash="dash", line_color="#c8102e", annotation_text="Target 70%")
fig2.update_layout(title="Loss Ratio by LoB (%)", yaxis=dict(range=[0,100]),
                   xaxis_tickangle=-30, yaxis_title="Loss Ratio %")

# ── Chart 3: GWP monthly trend ───────────────────────────────────────────────
fig3 = go.Figure()
fig3.add_trace(go.Bar(x=[d["month"] for d in trend], y=[d["gwp"] for d in trend],
                      name="GWP", marker_color="#1f4e79"))
fig3.add_trace(go.Bar(x=[d["month"] for d in trend], y=[d["nwp"] for d in trend],
                      name="NWP (net RI)", marker_color="#70ad47"))
fig3.update_layout(title="Monthly GWP / NWP Trend (EUR M)", barmode="overlay",
                   legend=dict(orientation="h", y=1.1), yaxis_title="EUR M")

# ── Chart 4: GWP by country ──────────────────────────────────────────────────
fig4 = px.bar(geo, x="gwp_eur_m", y="country", orientation="h",
              color="gwp_eur_m", color_continuous_scale="Blues",
              text="gwp_eur_m", title="GWP by Country (EUR M)")
fig4.update_traces(texttemplate="€%{text:.0f}M", textposition="outside")
fig4.update_layout(showlegend=False, coloraxis_showscale=False,
                   xaxis_title="", yaxis_title="")

# ── Chart 5: DQ score trend ──────────────────────────────────────────────────
fig5 = go.Figure()
fig5.add_trace(go.Scatter(x=[d["date"] for d in dq], y=[d["bronze_score"]*100 for d in dq],
                           name="Bronze", line=dict(color="#CD7F32", width=2)))
fig5.add_trace(go.Scatter(x=[d["date"] for d in dq], y=[d["silver_score"]*100 for d in dq],
                           name="Silver", line=dict(color="#808080", width=2)))
fig5.add_trace(go.Scatter(x=[d["date"] for d in dq], y=[d["gold_score"]*100 for d in dq],
                           name="Gold", line=dict(color="#DAA520", width=2)))
fig5.add_hline(y=95, line_dash="dash", line_color="#c8102e", annotation_text="Soglia 95%")
fig5.update_layout(title="Data Quality Score Trend — 30 giorni",
                   yaxis=dict(range=[93,100.5], ticksuffix="%"),
                   legend=dict(orientation="h", y=1.1))

# ── Chart 6: Broker scatter ──────────────────────────────────────────────────
fig6 = px.scatter(bp, x="gwp_eur_m", y="loss_ratio",
                  size="policy_count", color="retention_rate",
                  text="broker", hover_data=["share_pct"],
                  color_continuous_scale="RdYlGn", size_max=60,
                  title="Broker Performance")
fig6.add_hline(y=0.70, line_dash="dash", line_color="#c8102e", annotation_text="Loss Ratio Target")
fig6.update_traces(textposition="top center")
fig6.update_layout(xaxis_title="GWP (EUR M)", yaxis_title="Loss Ratio",
                   yaxis_tickformat=".0%",
                   coloraxis_colorbar=dict(title="Retention"))

# ── KPI cards HTML ───────────────────────────────────────────────────────────
def kpi_card(label, value, delta, delta_good=True):
    color = "#107c10" if delta_good else "#c8102e"
    return f"""
    <div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-delta" style="color:{color}">{delta}</div>
    </div>"""

kpi_html = "".join([
    kpi_card("GWP",           f"€{kpis['gwp_eur_m']:.0f}M",    "+6.2% YoY"),
    kpi_card("NWP",           f"€{kpis['nwp_eur_m']:.0f}M",    "+4.8% YoY"),
    kpi_card("Loss Ratio",    f"{kpis['loss_ratio']:.1%}",      "-1.2pp YoY"),
    kpi_card("Combined Ratio",f"{kpis['combined_ratio']:.1%}",  "-0.8pp YoY"),
    kpi_card("Policies",      f"{kpis['policy_count']:,}",      "+312"),
    kpi_card("Retention",     f"{kpis['renewal_retention_rate']:.1%}", "+1.4pp"),
    kpi_card("Active Claims", f"{kpis['active_claims']:,}",     "YTD"),
    kpi_card("Avg Premium",   f"€{kpis['avg_premium_eur']:,}",  "per policy"),
])

# ── Large losses table ───────────────────────────────────────────────────────
ll_rows = ""
for loss in ll:
    badge = f'<span class="badge-open">Open</span>' if loss["status"]=="Open" else f'<span class="badge-closed">Closed</span>'
    ll_rows += f"""<tr>
      <td>{loss['claim_number']}</td>
      <td>{loss['lob']}</td>
      <td>{loss['loss_type']}</td>
      <td>{loss['country']}</td>
      <td style="text-align:right;font-weight:600">€{loss['incurred_eur_m']:.2f}M</td>
      <td style="text-align:right">€{loss['net_eur_m']:.2f}M</td>
      <td>{badge}</td>
      <td>{loss['reported_date']}</td>
    </tr>"""

# ── Feature store table ──────────────────────────────────────────────────────
fs_rows = ""
for f in fs:
    status_cls = {"Active":"badge-active","Development":"badge-dev","Planned":"badge-plan"}.get(f["status"],"")
    drift = f'<span style="color:#c8102e">⚠ {f["drift"]}</span>' if f["drift"] else "—"
    fs_rows += f"""<tr>
      <td><strong>{f['use_case']}</strong></td>
      <td><span class="{status_cls}">{f['status']}</span></td>
      <td>{f['version']}</td>
      <td style="text-align:right">{f['features']}</td>
      <td style="text-align:right">{f['records']}</td>
      <td>{f['model_metric']}</td>
      <td>{drift}</td>
      <td>{f['last_updated']}</td>
    </tr>"""

# ── Assemble HTML ─────────────────────────────────────────────────────────────
now = datetime.now().strftime("%d %b %Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Data Platform — Corporate Insurance</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body   {{ font-family: 'Inter', 'Segoe UI', sans-serif; background:#f4f6f9; color:#1a1a2e; }}
  header {{ background:#1a1a2e; color:#fff; padding:1rem 2rem; display:flex; align-items:center; gap:1rem; position:sticky; top:0; z-index:99; box-shadow:0 2px 8px rgba(0,0,0,.3); }}
  header h1 {{ font-size:1.3rem; font-weight:700; }}
  header .sub {{ font-size:.85rem; opacity:.7; }}
  header .ts  {{ margin-left:auto; font-size:.8rem; opacity:.6; }}
  nav   {{ background:#fff; border-bottom:1px solid #e0e0e0; display:flex; gap:0; overflow-x:auto; }}
  nav a {{ padding:.8rem 1.4rem; text-decoration:none; color:#444; font-size:.9rem; font-weight:500;
           border-bottom:3px solid transparent; white-space:nowrap; }}
  nav a:hover, nav a.active {{ color:#c8102e; border-bottom-color:#c8102e; }}
  .page  {{ display:none; padding:1.5rem 2rem; max-width:1600px; margin:0 auto; }}
  .page.active {{ display:block; }}
  h2     {{ font-size:1.3rem; font-weight:700; margin-bottom:1rem; color:#1a1a2e; }}
  h3     {{ font-size:1rem; font-weight:600; margin:1.2rem 0 .5rem; color:#333; }}
  .kpi-row {{ display:flex; flex-wrap:wrap; gap:.8rem; margin-bottom:1.5rem; }}
  .kpi  {{ background:#fff; border-radius:10px; padding:.9rem 1.2rem; min-width:140px; flex:1;
           border-top:4px solid #c8102e; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .kpi-label {{ font-size:.75rem; color:#888; text-transform:uppercase; letter-spacing:.05em; }}
  .kpi-value {{ font-size:1.6rem; font-weight:700; margin:.2rem 0; }}
  .kpi-delta {{ font-size:.8rem; }}
  .grid-2 {{ display:grid; grid-template-columns:1fr 1fr; gap:1rem; }}
  .grid-3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem; }}
  .grid-1-2 {{ display:grid; grid-template-columns:1fr 2fr; gap:1rem; }}
  .card  {{ background:#fff; border-radius:10px; padding:1rem; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  table  {{ width:100%; border-collapse:collapse; font-size:.87rem; }}
  th     {{ background:#f0f4ff; padding:.6rem .8rem; text-align:left; font-weight:600; color:#333; border-bottom:2px solid #dde3f0; }}
  td     {{ padding:.55rem .8rem; border-bottom:1px solid #f0f0f0; }}
  tr:hover td {{ background:#fafbff; }}
  .badge-open   {{ background:#fff0f0; color:#c8102e; padding:.15rem .5rem; border-radius:12px; font-size:.78rem; font-weight:600; }}
  .badge-closed {{ background:#f0fff4; color:#107c10; padding:.15rem .5rem; border-radius:12px; font-size:.78rem; font-weight:600; }}
  .badge-active {{ background:#e8f5e9; color:#107c10; padding:.15rem .5rem; border-radius:12px; font-size:.78rem; }}
  .badge-dev    {{ background:#fff3e0; color:#d83b01; padding:.15rem .5rem; border-radius:12px; font-size:.78rem; }}
  .badge-plan   {{ background:#f5f5f5; color:#666;    padding:.15rem .5rem; border-radius:12px; font-size:.78rem; }}
  .arch  {{ background:#1a1a2e; color:#a8d8a0; padding:1rem 1.2rem; border-radius:8px; font-family:monospace; font-size:.83rem; line-height:1.6; overflow-x:auto; }}
  .alert {{ background:#fff8e1; border-left:4px solid #ffc000; padding:.7rem 1rem; border-radius:4px; font-size:.87rem; margin:.5rem 0; }}
  @media(max-width:800px) {{ .grid-2,.grid-3,.grid-1-2 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>

<header>
  <div>
    <h1>🏢 AI Data Platform</h1>
    <div class="sub">Corporate Insurance · Microsoft Fabric</div>
  </div>
  <div class="ts">Generated {now}</div>
</header>

<nav>
  <a href="#" class="active" onclick="show('portfolio',this)">📊 Portfolio</a>
  <a href="#" onclick="show('quality',this)">✅ Data Quality</a>
  <a href="#" onclick="show('broker',this)">🤝 Broker</a>
  <a href="#" onclick="show('features',this)">🧠 Feature Store</a>
  <a href="#" onclick="show('architecture',this)">🏗 Architecture</a>
</nav>

<!-- ═══ PORTFOLIO ═══════════════════════════════════════════════════════════ -->
<div id="page-portfolio" class="page active">
  <h2>📊 Portfolio Overview · YTD 2025</h2>
  <div class="kpi-row">{kpi_html}</div>

  <div class="grid-3">
    <div class="card">{fig_to_div(fig1, 360)}</div>
    <div class="card">{fig_to_div(fig2, 360)}</div>
    <div class="card">{fig_to_div(fig4, 360)}</div>
  </div>

  <div class="card" style="margin-top:1rem">{fig_to_div(fig3, 320)}</div>

  <div class="card" style="margin-top:1rem">
    <h3>Top Large Losses (&gt;€500K)</h3>
    <table>
      <thead><tr>
        <th>Claim #</th><th>LoB</th><th>Loss Type</th><th>Country</th>
        <th style="text-align:right">Incurred</th><th style="text-align:right">Net (RI)</th>
        <th>Status</th><th>Date</th>
      </tr></thead>
      <tbody>{ll_rows}</tbody>
    </table>
  </div>
</div>

<!-- ═══ DATA QUALITY ════════════════════════════════════════════════════════ -->
<div id="page-quality" class="page">
  <h2>✅ Data Quality Dashboard</h2>
  <div class="kpi-row">
    {kpi_card("Bronze Score","99.1%","+0.2pp")}
    {kpi_card("Silver Score","98.2%","-0.1pp",False)}
    {kpi_card("Gold Score","99.7%","+0.1pp")}
    {kpi_card("Open Issues","3","-2 resolved today")}
  </div>

  <div class="card">{fig_to_div(fig5, 340)}</div>

  <div class="card" style="margin-top:1rem">
    <h3>Issues Attivi</h3>
    <div class="alert">⚠️ <strong>missing_broker_id_high_premium</strong> · policy / Silver · 3 record<br>
      <small>Polizze &gt;€100K premio senza broker assegnato</small></div>
    <div class="alert">⚠️ <strong>claim_open_over_730_days</strong> · claim / Silver · 22 record<br>
      <small>Sinistri aperti &gt;730gg senza aggiornamento riserva</small></div>
    <div class="alert">⚠️ <strong>missing_industry_code</strong> · client / Silver · 8 record<br>
      <small>Clienti senza codice NACE/ATECO</small></div>
  </div>

  <div class="card" style="margin-top:1rem">
    <h3>Regole DQ — Riepilogo</h3>
    <table>
      <thead><tr><th>Layer</th><th>Severity</th><th>Definite</th><th>Passing</th><th>Failing</th></tr></thead>
      <tbody>
        <tr><td>Bronze</td><td>Critical</td><td>6</td><td>6</td><td>0</td></tr>
        <tr><td>Bronze</td><td>Warning</td><td>14</td><td>14</td><td>0</td></tr>
        <tr><td>Silver</td><td>Critical</td><td>8</td><td>8</td><td>0</td></tr>
        <tr><td>Silver</td><td>Warning</td><td>18</td><td>15</td><td style="color:#c8102e;font-weight:600">3</td></tr>
        <tr><td>Gold</td><td>Warning</td><td>12</td><td>12</td><td>0</td></tr>
      </tbody>
    </table>
  </div>
</div>

<!-- ═══ BROKER ══════════════════════════════════════════════════════════════ -->
<div id="page-broker" class="page">
  <h2>🤝 Broker Performance</h2>
  <div class="card">{fig_to_div(fig6, 420)}</div>
</div>

<!-- ═══ FEATURE STORE ═══════════════════════════════════════════════════════ -->
<div id="page-features" class="page">
  <h2>🧠 AI Feature Store</h2>
  <div class="kpi-row">
    {kpi_card("Use Case Attivi","3","—")}
    {kpi_card("In Sviluppo","1","—")}
    {kpi_card("Pianificati","1","—")}
    {kpi_card("Feature con Drift","1","broker_relationship_years",False)}
  </div>
  <div class="card">
    <table>
      <thead><tr>
        <th>Use Case</th><th>Status</th><th>Version</th><th style="text-align:right">Features</th>
        <th style="text-align:right">Records</th><th>Performance</th><th>Drift</th><th>Aggiornato</th>
      </tr></thead>
      <tbody>{fs_rows}</tbody>
    </table>
  </div>
</div>

<!-- ═══ ARCHITECTURE ════════════════════════════════════════════════════════ -->
<div id="page-architecture" class="page">
  <h2>🏗 System Architecture</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Multi-Agent System (Claude-powered)</h3>
      <div class="arch">OrchestratorAgent
  ├── IngestionAgent     ← Guidewire PC/CC/BC · Salesforce · AS400
  ├── TransformationAgent← Bronze → Silver → Gold
  ├── QualityAgent       ← DQ rules · quarantine · alerting
  ├── AIReadinessAgent   ← feature store · drift detection
  └── VisualizationAgent ← Power BI refresh · DAX generation</div>
      <h3 style="margin-top:1rem">Medallion Architecture (OneLake)</h3>
      <div class="arch">Bronze  ← raw landing, partition: year/month/day/source
Silver  ← cleansed, SCD Type 2, DQ validated
Gold    ← star schema, KPIs, AI features
        ↓
Power BI Semantic Model  +  Feature Store  +  ML APIs</div>
    </div>
    <div class="card">
      <h3>5 ML Use Cases</h3>
      <table>
        <thead><tr><th>Use Case</th><th>Target</th><th>Key Features</th></tr></thead>
        <tbody>
          <tr><td><strong>Claim Propensity</strong></td><td>P(claim in 12m)</td><td>TIV, loss ratio, LoB, country</td></tr>
          <tr><td><strong>Large Loss Predictor</strong></td><td>log(claim amount)</td><td>loss type, cat event, coverage limit</td></tr>
          <tr><td><strong>Renewal Churn</strong></td><td>P(non-renewal)</td><td>tenure, premium Δ, NPS, broker</td></tr>
          <tr><td><strong>UW Risk Score</strong></td><td>Risk grade (4 class)</td><td>nat-cat, industry, cyber maturity</td></tr>
          <tr><td><strong>Document AI</strong></td><td>Structured extraction</td><td>IDP on policy docs via Claude</td></tr>
        </tbody>
      </table>
      <h3 style="margin-top:1rem">Source Systems</h3>
      <table>
        <thead><tr><th>System</th><th>Type</th><th>Entities</th></tr></thead>
        <tbody>
          <tr><td>Guidewire PolicyCenter</td><td>JDBC/SQL</td><td>Policy, Coverage, Premium</td></tr>
          <tr><td>Guidewire ClaimCenter</td><td>JDBC/SQL</td><td>Claim, Exposure, Reserve</td></tr>
          <tr><td>Guidewire BillingCenter</td><td>JDBC/SQL</td><td>Invoice, Payment</td></tr>
          <tr><td>Salesforce CRM</td><td>REST API</td><td>Account, Contact, Opportunity</td></tr>
          <tr><td>AS400 Reinsurance</td><td>JDBC</td><td>RI Contract, RI Premium</td></tr>
          <tr><td>External Market Data</td><td>REST API</td><td>FX rates, Nat-Cat index</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<script>
function show(id, el) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
  document.getElementById('page-' + id).classList.add('active');
  el.classList.add('active');
  return false;
}}
</script>
</body>
</html>"""

out = os.path.join(os.path.dirname(__file__), "dashboard_export.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(out) // 1024
print(f"Generated: {out}  ({size_kb} KB)")
