"""
Corporate Insurance Platform - AI Data Platform
Prototype dashboard — runs fully locally.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from data.mock_data import (
    get_broker_performance,
    get_dq_trend,
    get_feature_store_summary,
    get_gwp_by_country,
    get_gwp_by_lob,
    get_gwp_monthly_trend,
    get_large_losses,
    get_loss_ratio_by_lob,
    get_pipeline_runs,
    get_portfolio_kpis,
    LOB_COLORS,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InsureCo · AI Data Platform",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.6rem; font-weight: 700; }
    .metric-card {
        background: #f8f9fa; border-radius: 8px; padding: 1rem;
        border-left: 4px solid #c8102e;
    }
    .status-ok  { color: #107c10; font-weight: 600; }
    .status-warn { color: #d83b01; font-weight: 600; }
    .status-err  { color: #c8102e; font-weight: 600; }
    .agent-msg { background:#f0f4ff; border-radius:8px; padding:0.8rem; margin:0.4rem 0; }
    div[data-testid="stSidebar"] { background: #1a1a2e; }
    div[data-testid="stSidebar"] * { color: #e8e8e8 !important; }
    div[data-testid="stSidebar"] .stRadio label { color: #e8e8e8 !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🦁 InsureCo")
    st.markdown("**AI Data Platform**")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "📊 Portfolio Overview",
            "⚙️ Pipeline Control",
            "💬 Agent Chat",
            "✅ Data Quality",
            "🧠 Feature Store",
            "📈 Reports",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.markdown("**Fabric Workspace**")
    st.code("insure-co", language=None)

    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if api_key_set:
        st.success("Claude: Connected")
    else:
        st.warning("Claude: Set ANTHROPIC_API_KEY")

    st.markdown(f"*{datetime.now().strftime('%d %b %Y  %H:%M')}*")


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 1 — PORTFOLIO OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
if page == "📊 Portfolio Overview":
    st.title("📊 Portfolio Overview")
    st.caption("Corporate Insurance Platform · YTD 2025")

    kpis = get_portfolio_kpis()

    # ── Row 1: headline KPIs ──────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("GWP", f"€{kpis['gwp_eur_m']:.0f}M", delta="+6.2% YoY")
    c2.metric("NWP", f"€{kpis['nwp_eur_m']:.0f}M", delta="+4.8% YoY")
    c3.metric("Loss Ratio", f"{kpis['loss_ratio']:.1%}", delta="-1.2pp YoY", delta_color="inverse")
    c4.metric("Combined Ratio", f"{kpis['combined_ratio']:.1%}", delta="-0.8pp YoY", delta_color="inverse")
    c5.metric("Policies", f"{kpis['policy_count']:,}", delta="+312")
    c6.metric("Retention", f"{kpis['renewal_retention_rate']:.1%}", delta="+1.4pp")

    st.divider()

    # ── Row 2: charts ──────────────────────────────────────────────────────
    col_left, col_mid, col_right = st.columns([1.2, 1.2, 1])

    with col_left:
        st.markdown("#### GWP by Line of Business")
        lob_data = get_gwp_by_lob()
        fig = px.pie(
            lob_data, values="gwp_eur_m", names="lob",
            color="lob", color_discrete_map=LOB_COLORS,
            hole=0.45,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(
            showlegend=False, margin=dict(l=10, r=10, t=10, b=10), height=320,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_mid:
        st.markdown("#### Loss Ratio by LoB")
        lr_data = get_loss_ratio_by_lob()
        colors = ["#c8102e" if d["status"] == "alert" else "#ed7d31" if d["status"] == "warning" else "#107c10" for d in lr_data]
        fig2 = go.Figure(go.Bar(
            x=[d["lob"] for d in lr_data],
            y=[d["loss_ratio"] * 100 for d in lr_data],
            marker_color=colors,
            text=[f"{d['loss_ratio']:.1%}" for d in lr_data],
            textposition="outside",
        ))
        fig2.add_hline(y=70, line_dash="dash", line_color="#c8102e", annotation_text="Target 70%")
        fig2.update_layout(
            yaxis_title="Loss Ratio %", height=320,
            margin=dict(l=10, r=10, t=10, b=60),
            xaxis_tickangle=-30,
            yaxis=dict(range=[0, 100]),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_right:
        st.markdown("#### GWP by Country")
        geo = get_gwp_by_country()
        fig3 = px.bar(
            geo, x="gwp_eur_m", y="country", orientation="h",
            color="gwp_eur_m", color_continuous_scale="Blues",
            text="gwp_eur_m",
        )
        fig3.update_traces(texttemplate="€%{text:.0f}M", textposition="outside")
        fig3.update_layout(
            showlegend=False, coloraxis_showscale=False,
            height=320, margin=dict(l=10, r=30, t=10, b=10),
            xaxis_title="", yaxis_title="",
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── Row 3: GWP trend + Large Losses ───────────────────────────────────
    col_trend, col_ll = st.columns([1.6, 1])

    with col_trend:
        st.markdown("#### Monthly GWP Trend")
        trend = get_gwp_monthly_trend(18)
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=[d["month"] for d in trend], y=[d["gwp"] for d in trend],
            name="GWP", marker_color="#1f4e79",
        ))
        fig4.add_trace(go.Bar(
            x=[d["month"] for d in trend], y=[d["nwp"] for d in trend],
            name="NWP (net RI)", marker_color="#70ad47",
        ))
        fig4.update_layout(
            barmode="overlay", height=300, legend=dict(orientation="h", y=1.1),
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis_title="EUR M",
        )
        st.plotly_chart(fig4, use_container_width=True)

    with col_ll:
        st.markdown("#### Top Large Losses (>€500K)")
        ll = get_large_losses(6)
        for loss in ll:
            color = "#c8102e" if loss["status"] == "Open" else "#107c10"
            st.markdown(
                f"**{loss['lob']}** · {loss['country']} "
                f"<span style='color:{color}'>●</span> "
                f"**€{loss['incurred_eur_m']:.1f}M** "
                f"*(net: €{loss['net_eur_m']:.1f}M)*  \n"
                f"<small>{loss['reported_date']} · {loss['loss_type']}</small>",
                unsafe_allow_html=True,
            )
            st.divider()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 2 — PIPELINE CONTROL
# ═══════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Pipeline Control":
    st.title("⚙️ Pipeline Control")

    # Platform health strip
    h1, h2, h3, h4, h5 = st.columns(5)
    h1.metric("Bronze Lakehouse", "Healthy", delta="6h ago")
    h2.metric("Silver Lakehouse", "Healthy", delta="6h ago")
    h3.metric("Gold Lakehouse", "Healthy", delta="6h ago")
    h4.metric("Semantic Model", "Healthy", delta="5h ago")
    h5.metric("Active Incidents", "0", delta="")

    st.divider()

    col_ctrl, col_runs = st.columns([1, 2])

    with col_ctrl:
        st.markdown("### Trigger Pipeline")
        pipeline_type = st.selectbox("Pipeline", [
            "🔄 Full Daily Pipeline",
            "⬇️  Ingestion Only",
            "🔀 Transformation Only",
            "✅ Quality Check",
            "🧠 AI Feature Refresh",
            "📊 BI Refresh",
        ])
        src = st.multiselect(
            "Source Systems",
            ["Guidewire PolicyCenter", "Guidewire ClaimCenter", "Salesforce CRM", "AS400 Reinsurance"],
            default=["Guidewire PolicyCenter", "Guidewire ClaimCenter", "Salesforce CRM"],
        )
        col_a, col_b = st.columns(2)
        skip_ai = col_a.checkbox("Skip AI", value=False)
        skip_bi = col_b.checkbox("Skip BI", value=False)

        if st.button("▶  Run Pipeline", type="primary", use_container_width=True):
            progress = st.progress(0, text="Initialising agents...")
            stages = [
                ("🔌 Connecting to Fabric...", 15),
                ("⬇️  Ingesting Bronze layer...", 35),
                ("✅ Validating Bronze...", 50),
                ("🔀 Transforming → Silver...", 65),
                ("🔀 Transforming → Gold...", 80),
                ("🧠 Refreshing features...", 92),
                ("📊 Refreshing BI model...", 100),
            ]
            for msg, pct in stages:
                time.sleep(0.4)
                progress.progress(pct, text=msg)
            st.success("Pipeline completed successfully! ✓  48,231 records processed · DQ 98.2%")

        st.divider()
        st.markdown("### DAG Status")
        dag_tasks = [
            ("ingest_guidewire_pc", "ingestion", "✅"),
            ("ingest_salesforce", "ingestion", "✅"),
            ("quality_bronze_policy", "quality", "✅"),
            ("transform_b2s_policy", "transform", "✅"),
            ("transform_b2s_claim", "transform", "✅"),
            ("quality_silver_policy", "quality", "⚠️"),
            ("transform_s2g_underwriting", "transform", "✅"),
            ("ai_features_claim_prop.", "ai_ready", "✅"),
            ("bi_refresh", "visualization", "✅"),
        ]
        for task, agent, icon in dag_tasks:
            st.markdown(f"{icon} `{task}` <small style='color:gray'>({agent})</small>", unsafe_allow_html=True)

    with col_runs:
        st.markdown("### Recent Pipeline Runs")
        runs = get_pipeline_runs()

        def _status_icon(s: str) -> str:
            return {"Succeeded": "✅", "Warning": "⚠️", "Failed": "❌"}.get(s, "🔵")

        for r in runs:
            icon = _status_icon(r["status"])
            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 0.8, 0.8, 0.8])
                c1.markdown(f"{icon} **{r['pipeline']}**  \n<small>{r['run_at']}</small>", unsafe_allow_html=True)
                c2.markdown(f"<small>{r['duration']}</small>", unsafe_allow_html=True)
                c3.markdown(f"<small>{r['records']}</small>", unsafe_allow_html=True)
                c4.markdown(f"<small>{r['dq_score']}</small>", unsafe_allow_html=True)
            st.divider()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 3 — AGENT CHAT
# ═══════════════════════════════════════════════════════════════════════════
elif page == "💬 Agent Chat":
    st.title("💬 Agent Chat")
    st.caption("Parla direttamente con l'OrchestratorAgent · powered by Claude")

    SUGGESTIONS = [
        "Esegui il pipeline giornaliero completo per tutti i source system",
        "Controlla la qualità dei dati nel Silver layer per le polizze",
        "Qual è il loss ratio per il ramo Cyber negli ultimi 12 mesi?",
        "Aggiorna le feature per il modello di Claim Propensity",
        "Genera l'estratto regolamentare IVASS per maggio 2025",
        "Ci sono sinistri aperti da più di 730 giorni senza aggiornamento riserva?",
    ]

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Ciao! Sono l'**OrchestratorAgent** di Corporate Insurance Platform.\n\n"
                    "Coordino l'intero stack dati su Microsoft Fabric: ingestione dai sistemi "
                    "Guidewire, trasformazioni Bronze→Silver→Gold, validazione qualità, "
                    "feature store ML, e refresh dei modelli Power BI.\n\n"
                    "Come posso aiutarti?"
                ),
            }
        ]

    # Suggestion chips
    if len(st.session_state.messages) <= 1:
        st.markdown("**Esempi di richieste:**")
        cols = st.columns(3)
        for i, sug in enumerate(SUGGESTIONS):
            if cols[i % 3].button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state._pending_prompt = sug

    # Render history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"], avatar="🦁" if msg["role"] == "assistant" else None):
            st.markdown(msg["content"])

    # Handle suggestion click
    pending = st.session_state.pop("_pending_prompt", None)
    prompt = st.chat_input("Chiedi all'Orchestrator...") or pending

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="🦁"):
            if not os.environ.get("ANTHROPIC_API_KEY"):
                response = (
                    "**ANTHROPIC_API_KEY non impostata.**\n\n"
                    "Per attivare la chat con Claude, imposta la variabile d'ambiente:\n"
                    "```bash\nexport ANTHROPIC_API_KEY=sk-ant-...\n```\n"
                    "Poi riavvia l'app con `streamlit run app/dashboard.py`"
                )
                st.markdown(response)
            else:
                import yaml
                from agents.orchestrator import OrchestratorAgent

                with open(os.path.join(ROOT, "config", "agents.yaml")) as f:
                    agent_cfg = yaml.safe_load(f)
                with open(os.path.join(ROOT, "config", "fabric.yaml")) as f:
                    fabric_cfg = yaml.safe_load(f)

                with st.spinner("L'Orchestrator sta elaborando..."):
                    orchestrator = OrchestratorAgent(agent_cfg, fabric_cfg)
                    result = orchestrator.run(task=prompt, task_id="dashboard-chat")
                    response = result.output or "✅ Task completato."

                typing_container = st.empty()
                displayed = ""
                for char in response:
                    displayed += char
                    typing_container.markdown(displayed + "▌")
                    time.sleep(0.008)
                typing_container.markdown(displayed)

            st.session_state.messages.append({"role": "assistant", "content": response})

        if len(st.session_state.messages) > 1:
            if st.button("🗑️ Nuova conversazione"):
                st.session_state.messages = [st.session_state.messages[0]]
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 4 — DATA QUALITY
# ═══════════════════════════════════════════════════════════════════════════
elif page == "✅ Data Quality":
    st.title("✅ Data Quality Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bronze Score", "99.1%", delta="+0.2pp")
    c2.metric("Silver Score", "98.2%", delta="-0.1pp", delta_color="inverse")
    c3.metric("Gold Score", "99.7%", delta="+0.1pp")
    c4.metric("Open Issues", "3", delta="-2 resolved today", delta_color="inverse")

    st.divider()

    col_trend, col_issues = st.columns([1.5, 1])

    with col_trend:
        st.markdown("#### DQ Score Trend (30 giorni)")
        dq = get_dq_trend(30)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[d["date"] for d in dq], y=[d["bronze_score"] * 100 for d in dq],
            name="Bronze", line=dict(color="#CD7F32", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=[d["date"] for d in dq], y=[d["silver_score"] * 100 for d in dq],
            name="Silver", line=dict(color="#808080", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=[d["date"] for d in dq], y=[d["gold_score"] * 100 for d in dq],
            name="Gold", line=dict(color="#DAA520", width=2),
        ))
        fig.add_hline(y=95, line_dash="dash", line_color="#c8102e", annotation_text="Soglia 95%")
        fig.update_layout(
            yaxis=dict(range=[93, 100.5], ticksuffix="%"),
            height=320, legend=dict(orientation="h", y=1.1),
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Completeness per Entity Type")
        completeness = {
            "Entity": ["policy", "claim", "client", "broker", "payment", "reserve"],
            "Bronze %": [99.4, 98.1, 97.8, 99.9, 99.2, 98.7],
            "Silver %": [98.9, 97.2, 96.4, 99.1, 98.8, 97.9],
            "Gold %":   [99.8, 99.1, 98.9, 99.7, 99.4, 99.0],
        }
        fig2 = go.Figure()
        for layer, color in [("Bronze %", "#CD7F32"), ("Silver %", "#808080"), ("Gold %", "#DAA520")]:
            fig2.add_trace(go.Bar(
                name=layer, x=completeness["Entity"], y=completeness[layer],
                marker_color=color,
            ))
        fig2.update_layout(
            barmode="group", height=260, yaxis=dict(range=[94, 101], ticksuffix="%"),
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_issues:
        st.markdown("#### Issues Attivi")
        issues = [
            {
                "severity": "⚠️ Warning",
                "rule": "missing_broker_id_high_premium",
                "entity": "policy / Silver",
                "count": 3,
                "description": "Polizze >€100K premio senza broker assegnato",
            },
            {
                "severity": "⚠️ Warning",
                "rule": "claim_open_over_730_days",
                "entity": "claim / Silver",
                "count": 22,
                "description": "Sinistri aperti >730gg senza aggiornamento riserva",
            },
            {
                "severity": "⚠️ Warning",
                "rule": "missing_industry_code",
                "entity": "client / Silver",
                "count": 8,
                "description": "Clienti senza codice NACE/ATECO",
            },
        ]
        for issue in issues:
            with st.expander(f"{issue['severity']} · `{issue['rule']}` ({issue['count']} record)"):
                st.markdown(f"**Entità:** {issue['entity']}")
                st.markdown(f"**Descrizione:** {issue['description']}")
                st.markdown(f"**Record coinvolti:** {issue['count']}")
                col_a, col_b = st.columns(2)
                col_a.button("Quarantina", key=f"q_{issue['rule']}", use_container_width=True)
                col_b.button("Ignora", key=f"i_{issue['rule']}", use_container_width=True)

        st.divider()
        st.markdown("#### Regole DQ — Riepilogo")
        rules_data = {
            "Layer": ["Bronze", "Bronze", "Silver", "Silver", "Gold"],
            "Severity": ["Critical", "Warning", "Critical", "Warning", "Warning"],
            "Definite": [6, 14, 8, 18, 12],
            "Passing": [6, 14, 8, 15, 12],
            "Failing": [0, 0, 0, 3, 0],
        }
        st.dataframe(rules_data, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Anomalie Rilevate (ultimi 7gg)")
        anomalies = [
            {"Campo": "total_insured_value", "Entity": "policy", "Z-score": "3.8", "Record": "POL-2025-04821"},
            {"Campo": "incurred_losses", "Entity": "claim", "Z-score": "4.2", "Record": "CLM-2025-00891"},
        ]
        st.dataframe(anomalies, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 5 — FEATURE STORE
# ═══════════════════════════════════════════════════════════════════════════
elif page == "🧠 Feature Store":
    st.title("🧠 AI Feature Store")
    st.caption("InsureCo · 5 use case ML · Microsoft Fabric Gold Layer")

    features = get_feature_store_summary()

    # Status summary
    active = sum(1 for f in features if f["status"] == "Active")
    dev = sum(1 for f in features if f["status"] == "Development")
    planned = sum(1 for f in features if f["status"] == "Planned")
    drifted = sum(1 for f in features if f["drift"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Use Case Attivi", active)
    m2.metric("In Sviluppo", dev)
    m3.metric("Pianificati", planned)
    m4.metric("Feature con Drift", drifted, delta_color="inverse" if drifted > 0 else "normal")

    st.divider()

    for feat in features:
        status_color = {"Active": "#107c10", "Development": "#d83b01", "Planned": "#666"}.get(feat["status"], "#666")
        expanded = feat["status"] == "Active"

        with st.expander(
            f"**{feat['use_case']}**  ·  "
            f"<span style='color:{status_color}'>{feat['status']}</span>  ·  "
            f"{feat['version']}",
            expanded=expanded,
        ):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Features", feat["features"])
            c2.metric("Record", feat["records"])
            c3.metric("Performance", feat["model_metric"])
            c4.metric("Aggiornato", feat["last_updated"])

            if feat["drift"]:
                st.warning(f"**Feature Drift Rilevato:** `{feat['drift']}` — Considerare ri-addestramento del modello.")

            if feat["status"] == "Active":
                st.markdown(f"**Tabella Fabric:** `{feat['table']}`")
                col_btn1, col_btn2, col_btn3, _ = st.columns([1, 1, 1, 2])
                col_btn1.button("Aggiorna Features", key=f"upd_{feat['use_case']}", use_container_width=True)
                col_btn2.button("Vedi Schema", key=f"sch_{feat['use_case']}", use_container_width=True)
                col_btn3.button("Export Dataset", key=f"exp_{feat['use_case']}", use_container_width=True)

    st.divider()

    col_arch, col_lob = st.columns(2)
    with col_arch:
        st.markdown("#### Feature Pipeline Architecture")
        st.code("""
Silver Layer
  ├── fact_policy    ──┐
  ├── fact_claim     ──┼──► FeatureAgent ──► gold.features_*
  ├── dim_client     ──┘          │
  └── external_data ─────────────┘
                                  │
                             Feature Store
                             (Delta + versioning)
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
              ML Training                  Real-time
              Datasets                     Scoring API
        """, language=None)

    with col_lob:
        st.markdown("#### Feature Count per Use Case")
        fig = px.bar(
            x=[f["use_case"] for f in features if f["features"] > 0],
            y=[f["features"] for f in features if f["features"] > 0],
            color=[f["status"] for f in features if f["features"] > 0],
            color_discrete_map={"Active": "#107c10", "Development": "#d83b01"},
            text=[f["features"] for f in features if f["features"] > 0],
        )
        fig.update_layout(
            showlegend=True, height=280, xaxis_tickangle=-20,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="", yaxis_title="# Features",
        )
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════
# PAGE 6 — REPORTS
# ═══════════════════════════════════════════════════════════════════════════
elif page == "📈 Reports":
    st.title("📈 Reports & Regulatory")

    tab_bi, tab_reg, tab_broker = st.tabs(["Power BI Reports", "Estratti Regolamentari", "Broker Performance"])

    with tab_bi:
        st.markdown("### Power BI Semantic Model")
        col_l, col_r = st.columns([1.2, 1])
        with col_l:
            reports = [
                {"Report": "Underwriting Dashboard", "Ultimo Refresh": "Oggi 06:18", "Stato": "✅ Fresh", "Utenti Attivi": 24},
                {"Report": "Claims Dashboard", "Ultimo Refresh": "Oggi 06:18", "Stato": "✅ Fresh", "Utenti Attivi": 18},
                {"Report": "Portfolio Dashboard", "Ultimo Refresh": "Ieri 06:15", "Stato": "⚠️ Stale", "Utenti Attivi": 31},
                {"Report": "Financial Dashboard", "Ultimo Refresh": "Oggi 06:19", "Stato": "✅ Fresh", "Utenti Attivi": 12},
                {"Report": "Broker Performance", "Ultimo Refresh": "Oggi 06:20", "Stato": "✅ Fresh", "Utenti Attivi": 9},
                {"Report": "Regulatory QRTs", "Ultimo Refresh": "01 Giu 2025", "Stato": "✅ Fresh", "Utenti Attivi": 5},
            ]
            st.dataframe(reports, use_container_width=True, hide_index=True)

            if st.button("🔄 Refresh Tutti i Report", type="primary"):
                with st.spinner("Triggering VisualizationAgent..."):
                    time.sleep(1.5)
                st.success("Refresh completato per tutti i 6 report.")

        with col_r:
            st.markdown("### DAX Measure Generator")
            kpi_sel = st.selectbox("KPI", [
                "gross_written_premium", "net_written_premium",
                "loss_ratio", "combined_ratio",
                "renewal_retention_rate", "large_loss_frequency",
            ])
            include_py = st.checkbox("Includi confronto PY", value=True)
            if st.button("Genera DAX", use_container_width=True):
                dax_map = {
                    "gross_written_premium": (
                        "[GWP EUR M] =\nDIVIDE(\n    CALCULATE(SUM(fact_premium[written_premium_eur])),\n    1000000\n)",
                        "#,0.0,, EUR M",
                    ),
                    "loss_ratio": (
                        "[Loss Ratio] =\nDIVIDE(\n    CALCULATE(SUM(fact_claim[total_incurred_eur])),\n    CALCULATE(SUM(fact_premium[earned_premium_eur])),\n    BLANK()\n)",
                        "0.0%",
                    ),
                    "combined_ratio": (
                        "[Combined Ratio] =\nDIVIDE(\n    CALCULATE(SUM(fact_claim[total_incurred_eur]))\n    + CALCULATE(SUM(fact_expense[total_expenses_eur])),\n    CALCULATE(SUM(fact_premium[earned_premium_eur])),\n    BLANK()\n)",
                        "0.0%",
                    ),
                    "renewal_retention_rate": (
                        "[Renewal Retention Rate] =\nDIVIDE(\n    COUNTROWS(FILTER(dim_policy, dim_policy[is_renewal] = TRUE())),\n    COUNTROWS(FILTER(dim_policy, dim_policy[prior_period_id] <> BLANK())),\n    BLANK()\n)",
                        "0.0%",
                    ),
                }
                dax, fmt = dax_map.get(kpi_sel, (f"-- DAX per {kpi_sel}", "#,0"))
                st.markdown("**Misura DAX:**")
                st.code(dax, language="sql")
                if include_py:
                    py_dax = f"[{kpi_sel} PY] = CALCULATE([{kpi_sel}], SAMEPERIODLASTYEAR(dim_date[date]))"
                    st.code(py_dax, language="sql")
                st.markdown(f"**Format string:** `{fmt}`")

    with tab_reg:
        st.markdown("### Estratti Regolamentari")
        col_l2, col_r2 = st.columns(2)
        with col_l2:
            report_type = st.selectbox("Tipo Report", [
                "Solvency II QRT (S.05.01 - Premi, Sinistri e Spese)",
                "Solvency II QRT (S.17.01 - Riserve Tecniche)",
                "IVASS Statistical Return",
                "IFRS 17 CSM Rollforward",
            ])
            period = st.text_input("Periodo di Riferimento (AAAA-MM)", value="2025-05")
            currency = st.selectbox("Valuta", ["EUR", "USD"])

            if st.button("📤 Genera Estratto", type="primary", use_container_width=True):
                with st.spinner("VisualizationAgent sta generando l'estratto..."):
                    time.sleep(2)
                st.success(
                    f"Estratto generato: `onelake/regulatory/{report_type[:20]}.../{period}/extract.xlsx`\n\n"
                    "Validazione XBRL: **Passed** · Record: 2,847"
                )
        with col_r2:
            st.markdown("#### Storico Estratti")
            history = [
                {"Tipo": "Solvency II QRT S.05.01", "Periodo": "2025-04", "Stato": "✅ Validato", "Generato": "01 Mag 2025"},
                {"Tipo": "IVASS Statistical", "Periodo": "2025-03", "Stato": "✅ Validato", "Generato": "02 Apr 2025"},
                {"Tipo": "IFRS 17 CSM", "Periodo": "2025-03", "Stato": "✅ Validato", "Generato": "05 Apr 2025"},
                {"Tipo": "Solvency II QRT S.17.01", "Periodo": "2025-03", "Stato": "⚠️ In Revisione", "Generato": "02 Apr 2025"},
            ]
            st.dataframe(history, use_container_width=True, hide_index=True)

    with tab_broker:
        st.markdown("### Broker Performance Analysis")
        bp = get_broker_performance()
        col_l3, col_r3 = st.columns([1.2, 1])
        with col_l3:
            fig = px.scatter(
                bp, x="gwp_eur_m", y="loss_ratio",
                size="policy_count", color="retention_rate",
                text="broker", hover_data=["share_pct", "policy_count"],
                color_continuous_scale="RdYlGn",
                size_max=60,
            )
            fig.add_hline(y=0.70, line_dash="dash", line_color="#c8102e", annotation_text="Loss Ratio Target 70%")
            fig.update_traces(textposition="top center")
            fig.update_layout(
                height=380, margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="GWP (EUR M)", yaxis_title="Loss Ratio",
                coloraxis_colorbar=dict(title="Retention"),
                yaxis_tickformat=".0%",
            )
            st.plotly_chart(fig, use_container_width=True)
        with col_r3:
            st.markdown("#### Top Broker by GWP")
            display = [
                {
                    "Broker": b["broker"],
                    "GWP (€M)": b["gwp_eur_m"],
                    "Loss Ratio": f"{b['loss_ratio']:.1%}",
                    "Retention": f"{b['retention_rate']:.1%}",
                    "Polizze": b["policy_count"],
                }
                for b in sorted(bp, key=lambda x: x["gwp_eur_m"], reverse=True)
            ]
            st.dataframe(display, use_container_width=True, hide_index=True)
