"""
Generali Corporate Commercial - AI Data Platform Dashboard
Control plane for the multi-agent Fabric data pipeline.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime

import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

st.set_page_config(
    page_title="Generali CC - AI Data Platform",
    page_icon="assets/generali_logo.png" if os.path.exists("assets/generali_logo.png") else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Header ──────────────────────────────────────────────────────────────────
st.title("Generali Corporate Commercial")
st.subheader("AI Data Platform - Microsoft Fabric Control Panel")
st.divider()

# ── Sidebar: Navigation ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio(
        "Select view",
        ["Pipeline Control", "Agent Chat", "Data Quality", "Feature Store", "Reports"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown("**Fabric Workspace**")
    st.code("generali-corporate-commercial", language=None)
    st.markdown("**Branch**")
    st.code("claude/generali-ai-data-platform", language=None)


# ── Pipeline Control Page ──────────────────────────────────────────────────
if page == "Pipeline Control":
    st.markdown("## Pipeline Control")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bronze Layer", "Healthy", delta="6h ago", delta_color="normal")
    col2.metric("Silver Layer", "Healthy", delta="6h ago", delta_color="normal")
    col3.metric("Gold Layer", "Healthy", delta="6h ago", delta_color="normal")
    col4.metric("Semantic Model", "Healthy", delta="5h ago", delta_color="normal")

    st.divider()

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown("### Trigger Pipeline")
        pipeline_type = st.selectbox(
            "Pipeline",
            [
                "Full Daily Pipeline",
                "Ingestion Only",
                "Transformation Only",
                "Quality Check",
                "AI Feature Refresh",
                "BI Refresh",
            ],
        )

        source_systems = st.multiselect(
            "Source Systems",
            ["policy_management", "claims_management", "billing", "crm", "reinsurance"],
            default=["policy_management", "claims_management", "billing", "crm"],
        )

        skip_ai = st.checkbox("Skip AI Readiness", value=False)
        skip_bi = st.checkbox("Skip BI Refresh", value=False)

        if st.button("Run Pipeline", type="primary", use_container_width=True):
            with st.spinner("Initialising agents..."):
                st.info(
                    "In production this triggers the OrchestratorAgent. "
                    "Set ANTHROPIC_API_KEY and Fabric credentials to activate."
                )
                st.success(f"Pipeline '{pipeline_type}' queued successfully.")

    with col_right:
        st.markdown("### Recent Runs")
        mock_runs = [
            {"Pipeline": "Full Daily Pipeline", "Status": "Succeeded", "Duration": "14m 32s", "Records": "48,231", "DQ Score": "98.2%", "Run At": "06:01 CET"},
            {"Pipeline": "BI Refresh", "Status": "Succeeded", "Duration": "3m 07s", "Records": "-", "DQ Score": "-", "Run At": "06:18 CET"},
            {"Pipeline": "AI Feature Refresh", "Status": "Succeeded", "Duration": "8m 14s", "Records": "42,381", "DQ Score": "-", "Run At": "06:20 CET"},
            {"Pipeline": "Quality Check (Silver)", "Status": "Warning", "Duration": "2m 41s", "Records": "12,543", "DQ Score": "96.1%", "Run At": "12:05 CET"},
        ]
        st.dataframe(mock_runs, use_container_width=True, hide_index=True)

        st.markdown("### Task DAG Status")
        dag_data = {
            "Task": ["ingest_guidewire_pc", "ingest_salesforce", "quality_bronze_policy",
                     "transform_b2s_policy", "quality_silver_policy", "transform_s2g_underwriting",
                     "ai_features_claim_propensity", "bi_refresh"],
            "Agent": ["ingestion", "ingestion", "quality", "transformation", "quality",
                      "transformation", "ai_readiness", "visualization"],
            "Status": ["Succeeded", "Succeeded", "Succeeded", "Succeeded", "Succeeded",
                       "Succeeded", "Succeeded", "Succeeded"],
            "Duration": ["1m 12s", "2m 03s", "0m 45s", "3m 21s", "1m 02s", "4m 18s", "8m 14s", "3m 07s"],
        }
        st.dataframe(dag_data, use_container_width=True, hide_index=True)


# ── Agent Chat Page ────────────────────────────────────────────────────────
elif page == "Agent Chat":
    st.markdown("## Agent Chat")
    st.info(
        "Chat directly with the OrchestratorAgent. It will delegate tasks to the appropriate "
        "sub-agents (ingestion, transformation, quality, AI readiness, visualization). "
        "Requires ANTHROPIC_API_KEY to be set."
    )

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Ciao! Sono l'Orchestrator Agent per Generali Corporate Commercial. "
                    "Posso aiutarti a gestire la piattaforma dati su Microsoft Fabric. "
                    "Chiedimi di eseguire pipeline, controllare la qualità dei dati, "
                    "preparare feature per ML, o generare report BI."
                ),
            }
        ]

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Chiedi all'Orchestrator..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            if not os.environ.get("ANTHROPIC_API_KEY"):
                response = (
                    "ANTHROPIC_API_KEY non configurata. "
                    "Imposta la variabile d'ambiente per attivare gli agenti AI."
                )
            else:
                import yaml
                from agents.orchestrator import OrchestratorAgent

                with open("config/agents.yaml") as f:
                    agent_cfg = yaml.safe_load(f)
                with open("config/fabric.yaml") as f:
                    fabric_cfg = yaml.safe_load(f)

                with st.spinner("L'Orchestrator sta elaborando..."):
                    orchestrator = OrchestratorAgent(agent_cfg, fabric_cfg)
                    result = orchestrator.run(task=prompt)
                    response = result.output or "Task completato senza output testuale."

            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})


# ── Data Quality Page ──────────────────────────────────────────────────────
elif page == "Data Quality":
    st.markdown("## Data Quality Dashboard")

    import plotly.graph_objects as go

    col1, col2, col3 = st.columns(3)
    col1.metric("Bronze DQ Score", "99.1%", delta="+0.2% vs yesterday")
    col2.metric("Silver DQ Score", "98.2%", delta="-0.1% vs yesterday")
    col3.metric("Gold DQ Score", "99.7%", delta="+0.1% vs yesterday")

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### DQ Score Trend (30 days)")
        import plotly.express as px
        from datetime import timedelta
        import random

        dates = [(datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(30, 0, -1)]
        bronze_scores = [round(0.991 + random.uniform(-0.003, 0.003), 4) for _ in dates]
        silver_scores = [round(0.982 + random.uniform(-0.005, 0.005), 4) for _ in dates]
        gold_scores = [round(0.997 + random.uniform(-0.001, 0.001), 4) for _ in dates]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=bronze_scores, name="Bronze", line=dict(color="#CD7F32")))
        fig.add_trace(go.Scatter(x=dates, y=silver_scores, name="Silver", line=dict(color="#C0C0C0")))
        fig.add_trace(go.Scatter(x=dates, y=gold_scores, name="Gold", line=dict(color="#FFD700")))
        fig.add_hline(y=0.95, line_dash="dash", line_color="red", annotation_text="Threshold 95%")
        fig.update_layout(yaxis_tickformat=".1%", height=350, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("### Active Quality Issues")
        issues = [
            {"Rule": "missing_broker_id_high_premium", "Severity": "Warning", "Count": 3, "Entity": "policy", "Layer": "Silver"},
            {"Rule": "claim_open_over_730_days", "Severity": "Warning", "Count": 22, "Entity": "claim", "Layer": "Silver"},
            {"Rule": "missing_industry_code", "Severity": "Warning", "Count": 8, "Entity": "client", "Layer": "Silver"},
        ]
        st.dataframe(issues, use_container_width=True, hide_index=True)
        st.markdown("### Quality Rules Summary")
        rules_summary = {
            "Category": ["Critical", "Warning", "Info"],
            "Defined": [12, 28, 15],
            "Passing": [12, 25, 15],
            "Failing": [0, 3, 0],
        }
        st.dataframe(rules_summary, use_container_width=True, hide_index=True)


# ── Feature Store Page ─────────────────────────────────────────────────────
elif page == "Feature Store":
    st.markdown("## AI Feature Store")

    use_cases = {
        "claim_propensity": {
            "status": "Active",
            "version": "v3",
            "features": 11,
            "records": "42,381",
            "last_updated": "Today 06:20",
            "drift": "None",
            "model_accuracy": "AUC 0.847",
        },
        "large_loss_predictor": {
            "status": "Active",
            "version": "v2",
            "features": 9,
            "records": "8,234",
            "last_updated": "Today 06:22",
            "drift": "None",
            "model_accuracy": "RMSE 0.312",
        },
        "renewal_churn": {
            "status": "Active",
            "version": "v2",
            "features": 7,
            "records": "18,920",
            "last_updated": "Today 06:24",
            "drift": "Warning: broker_relationship_years",
            "model_accuracy": "AUC 0.781",
        },
        "underwriting_risk_score": {
            "status": "Development",
            "version": "v1",
            "features": 8,
            "records": "15,432",
            "last_updated": "Yesterday 06:18",
            "drift": "None",
            "model_accuracy": "F1 0.723",
        },
        "document_ai": {
            "status": "Planned",
            "version": "-",
            "features": 0,
            "records": "-",
            "last_updated": "-",
            "drift": "-",
            "model_accuracy": "-",
        },
    }

    for name, info in use_cases.items():
        status_color = {"Active": "green", "Development": "orange", "Planned": "gray"}.get(info["status"], "gray")
        with st.expander(f"{name.replace('_', ' ').title()} — {info['status']}", expanded=info["status"] == "Active"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Version", info["version"])
            c2.metric("Features", info["features"])
            c3.metric("Records", info["records"])
            c4.metric("Model Performance", info["model_accuracy"])
            if info["drift"] and info["drift"] != "None" and info["drift"] != "-":
                st.warning(f"Feature Drift Detected: {info['drift']}")
            st.caption(f"Last updated: {info['last_updated']}")


# ── Reports Page ───────────────────────────────────────────────────────────
elif page == "Reports":
    st.markdown("## Reports & Regulatory Extracts")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### BI Reports (Power BI)")
        reports = [
            {"Report": "Underwriting Dashboard", "Last Refresh": "Today 06:18", "Status": "Fresh"},
            {"Report": "Claims Dashboard", "Last Refresh": "Today 06:18", "Status": "Fresh"},
            {"Report": "Portfolio Dashboard", "Last Refresh": "Yesterday 06:15", "Status": "Stale"},
            {"Report": "Financial Dashboard", "Last Refresh": "Today 06:19", "Status": "Fresh"},
            {"Report": "Broker Performance", "Last Refresh": "Today 06:20", "Status": "Fresh"},
        ]
        st.dataframe(reports, use_container_width=True, hide_index=True)

        if st.button("Refresh All Reports", use_container_width=True):
            st.info("Triggering VisualizationAgent to refresh all semantic models...")

    with col2:
        st.markdown("### Regulatory Extracts")
        period = st.text_input("Reference Period (YYYY-MM)", value=datetime.utcnow().strftime("%Y-%m"))
        report_type = st.selectbox(
            "Report Type",
            ["solvency_ii_qrt", "ivass_statistical", "ifrs17_csg"],
        )
        if st.button("Generate Extract", use_container_width=True):
            st.success(
                f"Extract '{report_type}' for period {period} queued. "
                "Output will be written to OneLake/regulatory/."
            )
