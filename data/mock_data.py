"""
Mock insurance data for Generali Corporate Commercial prototype.
Realistic Italian/European corporate insurance portfolio.
"""
from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

random.seed(42)

# ── Lines of Business ─────────────────────────────────────────────────────
LINES_OF_BUSINESS = [
    "Property",
    "General Liability",
    "D&O",
    "Marine Cargo",
    "Engineering",
    "Cyber",
    "Credit & Surety",
    "Aviation",
]

LOB_COLORS = {
    "Property": "#1f4e79",
    "General Liability": "#2e75b6",
    "D&O": "#4472c4",
    "Marine Cargo": "#70ad47",
    "Engineering": "#ed7d31",
    "Cyber": "#ff0000",
    "Credit & Surety": "#ffc000",
    "Aviation": "#7030a0",
}

LOB_WEIGHTS = [0.32, 0.22, 0.12, 0.10, 0.09, 0.07, 0.05, 0.03]

# ── Countries ─────────────────────────────────────────────────────────────
TOP_COUNTRIES = ["IT", "DE", "FR", "ES", "NL", "GB", "BE", "AT", "CH", "PL"]
COUNTRY_NAMES = {
    "IT": "Italy", "DE": "Germany", "FR": "France", "ES": "Spain",
    "NL": "Netherlands", "GB": "United Kingdom", "BE": "Belgium",
    "AT": "Austria", "CH": "Switzerland", "PL": "Poland",
}
COUNTRY_WEIGHTS = [0.38, 0.18, 0.12, 0.08, 0.07, 0.06, 0.04, 0.03, 0.02, 0.02]

# ── Industries ────────────────────────────────────────────────────────────
INDUSTRIES = [
    "Manufacturing", "Retail & Distribution", "Energy & Utilities",
    "Financial Services", "Healthcare", "Transport & Logistics",
    "Construction", "Technology", "Food & Beverage", "Chemicals",
]

# ── Source Systems ────────────────────────────────────────────────────────
SOURCE_SYSTEMS = [
    "Guidewire PolicyCenter",
    "Guidewire ClaimCenter",
    "Salesforce CRM",
    "AS400 Reinsurance",
    "BillingCenter",
]


def _rand_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _rand_premium() -> float:
    """Return a premium amount in EUR (log-normal distribution)."""
    import math
    return round(math.exp(random.gauss(11, 1.8)), -2)


# ── Portfolio KPIs ────────────────────────────────────────────────────────
def get_portfolio_kpis() -> dict:
    return {
        "gwp_eur_m": 463.2,
        "nwp_eur_m": 318.7,  # after reinsurance
        "earned_premium_eur_m": 441.8,
        "incurred_losses_eur_m": 278.3,
        "expenses_eur_m": 141.4,
        "loss_ratio": 0.630,
        "expense_ratio": 0.320,
        "combined_ratio": 0.950,
        "policy_count": 14_823,
        "active_claims": 2_341,
        "large_losses_ytd": 18,  # > 500K EUR
        "renewal_retention_rate": 0.867,
        "new_business_hit_rate": 0.312,
        "avg_premium_eur": 31_248,
        "total_insured_value_eur_b": 142.7,
        "reinsurance_recoverable_eur_m": 22.4,
    }


def get_gwp_by_lob() -> list[dict]:
    total = 463.2
    return [
        {"lob": lob, "gwp_eur_m": round(total * w, 1), "weight": round(w * 100, 1)}
        for lob, w in zip(LINES_OF_BUSINESS, LOB_WEIGHTS)
    ]


def get_gwp_monthly_trend(months: int = 18) -> list[dict]:
    data = []
    base = datetime(2024, 1, 1)
    for i in range(months):
        dt = base + timedelta(days=30 * i)
        seasonal = 1.0 + 0.08 * (1 if dt.month in [1, 3, 9, 10] else 0)
        gwp = round(random.gauss(25.7 * seasonal, 1.8), 1)
        nwp = round(gwp * random.uniform(0.67, 0.71), 1)
        data.append({
            "month": dt.strftime("%b %Y"),
            "month_dt": dt,
            "gwp": gwp,
            "nwp": nwp,
        })
    return data


def get_loss_ratio_by_lob() -> list[dict]:
    loss_ratios = {
        "Property": 0.72,
        "General Liability": 0.54,
        "D&O": 0.61,
        "Marine Cargo": 0.58,
        "Engineering": 0.48,
        "Cyber": 0.82,
        "Credit & Surety": 0.45,
        "Aviation": 0.63,
    }
    gwp_by_lob = {item["lob"]: item["gwp_eur_m"] for item in get_gwp_by_lob()}
    return [
        {
            "lob": lob,
            "loss_ratio": lr,
            "earned_premium_m": round(gwp_by_lob[lob] * 0.95, 1),
            "incurred_losses_m": round(gwp_by_lob[lob] * 0.95 * lr, 1),
            "status": "alert" if lr > 0.75 else "warning" if lr > 0.65 else "ok",
        }
        for lob, lr in loss_ratios.items()
    ]


def get_gwp_by_country() -> list[dict]:
    total = 463.2
    return [
        {
            "country_code": cc,
            "country": COUNTRY_NAMES[cc],
            "gwp_eur_m": round(total * w, 1),
        }
        for cc, w in zip(TOP_COUNTRIES, COUNTRY_WEIGHTS)
    ]


def get_large_losses(n: int = 18) -> list[dict]:
    losses = []
    for i in range(n):
        lob = random.choice(["Property", "Cyber", "D&O", "Marine Cargo", "Engineering"])
        amount = round(random.uniform(0.5, 8.5), 2)
        ri_share = round(random.uniform(0.3, 0.8) if amount > 2.0 else 0, 2)
        losses.append({
            "claim_number": f"GCC-{2024 + i // 12}-{10000 + i}",
            "lob": lob,
            "loss_type": random.choice(["Fire", "Flood", "Cyber Incident", "D&O Claim", "Cargo Damage"]),
            "country": random.choice(TOP_COUNTRIES),
            "incurred_eur_m": amount,
            "ri_recoverable_eur_m": round(amount * ri_share, 2),
            "net_eur_m": round(amount * (1 - ri_share), 2),
            "status": random.choice(["Open", "Open", "Open", "Closed"]),
            "reported_date": _rand_date(date(2024, 1, 1), date(2025, 12, 31)).isoformat(),
        })
    losses.sort(key=lambda x: x["incurred_eur_m"], reverse=True)
    return losses


def get_broker_performance() -> list[dict]:
    brokers = [
        ("Marsh Italia", "IT", 0.19),
        ("Aon Italy", "IT", 0.15),
        ("Willis Towers Watson IT", "IT", 0.12),
        ("Howden Italy", "IT", 0.09),
        ("AON GCC", "DE", 0.07),
        ("Lockton EMEA", "GB", 0.06),
        ("Gallagher Italy", "IT", 0.05),
        ("BMS Group", "GB", 0.04),
        ("Others", "EU", 0.23),
    ]
    total_gwp = 463.2
    return [
        {
            "broker": name,
            "country": cc,
            "gwp_eur_m": round(total_gwp * share, 1),
            "loss_ratio": round(random.uniform(0.48, 0.74), 3),
            "policy_count": int(14823 * share * random.uniform(0.8, 1.2)),
            "retention_rate": round(random.uniform(0.81, 0.94), 3),
            "share_pct": round(share * 100, 1),
        }
        for name, cc, share in brokers
    ]


def get_dq_trend(days: int = 30) -> list[dict]:
    data = []
    base_date = datetime.utcnow() - timedelta(days=days)
    for i in range(days):
        dt = base_date + timedelta(days=i)
        data.append({
            "date": dt.strftime("%Y-%m-%d"),
            "bronze_score": round(min(1.0, random.gauss(0.991, 0.003)), 4),
            "silver_score": round(min(1.0, random.gauss(0.982, 0.005)), 4),
            "gold_score": round(min(1.0, random.gauss(0.997, 0.001)), 4),
        })
    return data


def get_pipeline_runs(n: int = 20) -> list[dict]:
    pipelines = [
        "ingest_guidewire_pc", "ingest_salesforce", "transform_b2s_policy",
        "transform_b2s_claim", "quality_silver_policy", "transform_s2g_underwriting",
        "transform_s2g_claims", "ai_features_claim_propensity", "bi_refresh",
    ]
    runs = []
    base = datetime.utcnow() - timedelta(hours=8)
    for i in range(n):
        pipeline = pipelines[i % len(pipelines)]
        status = random.choices(["Succeeded", "Succeeded", "Succeeded", "Warning", "Failed"], weights=[70, 10, 10, 7, 3])[0]
        runs.append({
            "run_at": (base + timedelta(minutes=i * 22)).strftime("%H:%M"),
            "pipeline": pipeline,
            "status": status,
            "duration": f"{random.randint(1, 14)}m {random.randint(5, 59):02d}s",
            "records": f"{random.randint(800, 48000):,}",
            "dq_score": f"{random.uniform(95.0, 99.8):.1f}%" if status != "Failed" else "-",
        })
    return list(reversed(runs[:10]))


def get_feature_store_summary() -> list[dict]:
    return [
        {
            "use_case": "Claim Propensity",
            "table": "gold.features_claim_propensity_v3",
            "status": "Active",
            "version": "v3",
            "features": 11,
            "records": "42,381",
            "model_metric": "AUC 0.847",
            "last_updated": "Today 06:20",
            "drift": None,
        },
        {
            "use_case": "Large Loss Predictor",
            "table": "gold.features_large_loss_v2",
            "status": "Active",
            "version": "v2",
            "features": 9,
            "records": "8,234",
            "model_metric": "RMSE 0.312",
            "last_updated": "Today 06:22",
            "drift": None,
        },
        {
            "use_case": "Renewal Churn",
            "table": "gold.features_renewal_churn_v2",
            "status": "Active",
            "version": "v2",
            "features": 7,
            "records": "18,920",
            "model_metric": "AUC 0.781",
            "last_updated": "Today 06:24",
            "drift": "broker_relationship_years",
        },
        {
            "use_case": "Underwriting Risk Score",
            "table": "gold.features_uw_risk_v1",
            "status": "Development",
            "version": "v1",
            "features": 8,
            "records": "15,432",
            "model_metric": "F1 0.723",
            "last_updated": "Yesterday 06:18",
            "drift": None,
        },
        {
            "use_case": "Document AI (IDP)",
            "table": "-",
            "status": "Planned",
            "version": "-",
            "features": 0,
            "records": "-",
            "model_metric": "-",
            "last_updated": "-",
            "drift": None,
        },
    ]
