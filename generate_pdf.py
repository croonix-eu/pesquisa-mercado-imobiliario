"""
Generate A4 PDF report from the same data as the Streamlit dashboard.
Usage: python generate_pdf.py
Output: report.pdf
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from weasyprint import HTML

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
AGENT_IDS = [35066445, 35066465, 35066248]
OUTPUT_PATH = Path(__file__).resolve().parent / "report.pdf"

SINTRA_CENTER = (38.7979, -9.3817)
CASCAIS_CENTER = (38.6967, -9.4217)
LISBON_CENTER = (38.7223, -9.1393)

CHART_COLORS = {
    "ocean": "#1B5E8C",
    "terra": "#C2703E",
    "pos": "#2D7D5F",
    "neg": "#B83D3D",
    "muted": "#8c8c8c",
}

FEAT_NAMES = {
    "area_bruta_sqm": "Área bruta (m²)",
    "dist_sintra_km": "Distância a Sintra (km)",
    "dist_beach_km": "Distância à praia (km)",
    "num_rooms": "Número de quartos",
    "dist_cascais_km": "Distância a Cascais (km)",
    "num_bathrooms": "Casas de banho",
    "dist_lisbon_km": "Distância a Lisboa (km)",
    "pool": "Piscina",
    "terrace": "Terraço",
    "garden": "Jardim",
    "is_to_renovate": "Para recuperar",
    "is_new": "Construção nova",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


def fmt_eur(v):
    if pd.isna(v):
        return "—"
    return f"€{v:,.0f}".replace(",", ".")


def fig_to_svg(fig, width=700, height=350):
    return fig.to_image(format="svg", width=width, height=height).decode("utf-8")


# ---------------------------------------------------------------------------
# Data loading (same logic as app.py, without Streamlit cache)
# ---------------------------------------------------------------------------
def load_data():
    listings = pd.read_csv(DATA_DIR / "listings.csv")
    details = pd.read_csv(DATA_DIR / "details.csv")
    enrichment = pd.read_csv(DATA_DIR / "enrichment.csv")

    df = listings.merge(details, on="listing_id", how="left").merge(enrichment, on="listing_id", how="left")
    df = df.dropna(subset=["price_eur", "area_bruta_sqm", "latitude", "longitude"])
    df = df[df["price_eur"] > 0]
    df = df[df["area_bruta_sqm"] > 0]
    df["price_per_sqm"] = df["price_eur"] / df["area_bruta_sqm"]

    beaches = [
        (38.8379, -9.4611), (38.8458, -9.4421), (38.8246, -9.4639),
        (38.8139, -9.4714), (38.7893, -9.4833), (38.7283, -9.4747),
        (38.7069, -9.4594), (38.6797, -9.3361), (38.6867, -9.3194),
    ]
    beach_dists = [haversine(df["latitude"], df["longitude"], b[0], b[1]) for b in beaches]
    df["dist_beach_km"] = np.column_stack(beach_dists).min(axis=1)
    df["dist_sintra_km"] = haversine(df["latitude"], df["longitude"], *SINTRA_CENTER)
    df["dist_cascais_km"] = haversine(df["latitude"], df["longitude"], *CASCAIS_CENTER)
    df["dist_lisbon_km"] = haversine(df["latitude"], df["longitude"], *LISBON_CENTER)
    df["num_rooms"] = df["tipologia"].str.extract(r"T(\d+)").astype(float)

    for col in ["num_bathrooms", "num_rooms"]:
        df[col] = df[col].fillna(df[col].median())

    df["is_agent"] = df["listing_id"].isin(AGENT_IDS)
    df["area_util_sqm"] = pd.to_numeric(df["area_util_sqm"], errors="coerce")

    # LSF classification
    desc = df["description_full"].fillna("").str.lower()
    lsf_explicit = desc.str.contains(
        r"lsf|light steel|steel frame|aço leve|construção seca|ossatura met[aá]lica", regex=True)
    has_etics = desc.str.contains("etics", case=False)
    has_efficiency = desc.str.contains(
        r"eficiência energética|isolamento térmico|desempenho térmico|eficiencia energetica", regex=True)
    has_modular = desc.str.contains(r"modular|pré-fabricad|pre-fabricad", regex=True)
    has_traditional = desc.str.contains(
        r"betão armado|betao armado|alvenaria|tijolo|construção tradicional|pedra aparelhada", regex=True)
    is_new = (
        (df["condition"] == "Empreendimento de nova construção")
        | desc.str.contains("construção nova|construccion nueva", regex=True)
    )
    cert = df["energy_certificate"].fillna("").str.upper()
    has_good_cert = cert.str.contains(r"^A\+?$", regex=True)
    year = pd.to_numeric(df["year_built"], errors="coerce")
    is_recent = year >= 2020

    score = pd.Series(0.0, index=df.index)
    score += lsf_explicit * 0.50
    score += has_etics * 0.25
    score += has_modular * 0.20
    score += has_efficiency * 0.10
    score += is_new * 0.10
    score += has_good_cert * 0.05
    score += is_recent * 0.05
    score -= has_traditional * 0.30
    score = score.clip(0, 1)
    score.loc[df["is_agent"]] = 0.90

    df["lsf_score"] = score
    df["construction_type"] = pd.cut(
        score, bins=[-0.01, 0.10, 0.25, 1.01],
        labels=["Tradicional", "Indeterminado", "Provável LSF"],
    )

    AGENT_AREA_HABITACAO = 223.91
    agent_mask = df["is_agent"]
    df.loc[agent_mask, "area_bruta_sqm"] = AGENT_AREA_HABITACAO
    df.loc[agent_mask, "area_util_sqm"] = AGENT_AREA_HABITACAO
    df.loc[agent_mask, "price_per_sqm"] = df.loc[agent_mask, "price_eur"] / AGENT_AREA_HABITACAO

    return df


def run_regression(df):
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_score, cross_val_predict

    features = [
        "area_bruta_sqm", "dist_sintra_km", "dist_beach_km", "num_rooms",
        "dist_cascais_km", "num_bathrooms", "dist_lisbon_km",
    ]
    binary_features = {"pool": "has_pool", "terrace": "has_terrace", "garden": "has_garden"}
    condition_features = {
        "is_to_renovate": lambda x: (x == "Segunda mão/para recuperar").astype(int),
        "is_new": lambda x: (x == "Empreendimento de nova construção").astype(int),
    }

    model_df = df.copy()
    for feat_name, col in binary_features.items():
        model_df[feat_name] = model_df[col].fillna(False).astype(int)
        features.append(feat_name)
    for feat_name, fn in condition_features.items():
        model_df[feat_name] = fn(model_df["condition"])
        features.append(feat_name)

    model_df = model_df.dropna(subset=features + ["price_per_sqm"])
    X = model_df[features].values
    y = model_df["price_per_sqm"].values

    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.1, subsample=0.8, random_state=42)
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    r2 = cv_scores.mean()
    oof_preds = cross_val_predict(model, X, y, cv=5)
    model.fit(X, y)

    importances = dict(zip(features, model.feature_importances_))
    model_df = model_df.copy()
    model_df["predicted"] = oof_preds
    model_df["residual_pct"] = ((model_df["price_per_sqm"] - oof_preds) / oof_preds * 100).round(1)

    agent_rows = model_df[model_df["is_agent"]]
    agent_pred = agent_rows["predicted"].mean() if len(agent_rows) > 0 else None

    return {
        "r2": r2,
        "n": len(model_df),
        "importances": importances,
        "predictions": model_df[["listing_id", "price_per_sqm", "predicted", "residual_pct", "is_agent"]],
        "agent_pred": agent_pred,
        "features": features,
    }


def get_comparables(df):
    agent = df[df["is_agent"]].iloc[0]
    lat, lon = agent["latitude"], agent["longitude"]
    df_c = df.copy()
    df_c["dist_to_agent"] = haversine(df_c["latitude"], df_c["longitude"], lat, lon)
    nearby = df_c[df_c["dist_to_agent"] <= 3.0].copy()
    nearby = nearby[nearby["num_rooms"].between(3, 5)]
    nearby = nearby[nearby["condition"] == "Segunda mão/bom estado"]
    nearby = nearby[nearby["has_pool"] != True]  # noqa: E712
    return nearby.sort_values("price_eur")


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
def build_percentile_chart(pct_data):
    fig = go.Figure()
    for label, pct in reversed(pct_data):
        color = CHART_COLORS["neg"] if pct >= 50 else CHART_COLORS["pos"]
        fig.add_trace(go.Bar(
            y=[label], x=[pct], orientation="h",
            marker_color=color, opacity=0.8,
            text=[f"P{pct:.0f}"], textposition="outside",
            textfont=dict(size=12, color=color),
        ))
    fig.add_vline(x=50, line_dash="dot", line_color="#999", line_width=1,
                  annotation_text="Mediana", annotation_position="top")
    fig.update_layout(
        height=280, showlegend=False,
        xaxis=dict(range=[0, 105], title="Percentil", showgrid=True, gridcolor="#eee"),
        yaxis=dict(automargin=True),
        margin=dict(l=10, r=50, t=20, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_condition_chart(cond_stats, agent_psqm):
    cond_colors = {"Construção nova": "#2D7D5F", "Bom estado": CHART_COLORS["ocean"], "Para recuperar": CHART_COLORS["muted"]}
    fig = go.Figure()
    for _, row in cond_stats.iterrows():
        label = row["label"]
        fig.add_trace(go.Bar(
            x=[label], y=[row["median_psqm"]],
            marker_color=cond_colors.get(label, CHART_COLORS["ocean"]),
            text=[f"€{row['median_psqm']:,.0f}/m²".replace(",", ".")],
            textposition="outside", textfont=dict(size=12),
        ))
    fig.add_hline(y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["terra"], line_width=2,
                  annotation_text=f"Alvo: €{agent_psqm:,.0f}/m²".replace(",", "."),
                  annotation_font_color=CHART_COLORS["terra"], annotation_position="top left")
    fig.update_layout(
        height=300, showlegend=False,
        yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor="#eee"),
        margin=dict(l=10, r=10, t=20, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_lsf_chart(lsf_stats, agent_psqm):
    ct_order = ["Provável LSF", "Indeterminado", "Tradicional"]
    ct_colors = {"Provável LSF": CHART_COLORS["terra"], "Indeterminado": CHART_COLORS["muted"], "Tradicional": CHART_COLORS["ocean"]}
    fig = go.Figure()
    for ct in ct_order:
        row = lsf_stats[lsf_stats["construction_type"] == ct]
        if len(row) == 0:
            continue
        row = row.iloc[0]
        fig.add_trace(go.Bar(
            x=[ct], y=[row["median_psqm"]],
            marker_color=ct_colors[ct],
            text=[f"€{row['median_psqm']:,.0f}/m²".replace(",", ".")],
            textposition="outside", textfont=dict(size=12),
        ))
    fig.add_hline(y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["terra"], line_width=2,
                  annotation_text=f"Alvo (LSF): €{agent_psqm:,.0f}/m²".replace(",", "."),
                  annotation_font_color=CHART_COLORS["terra"], annotation_position="top left")
    fig.update_layout(
        height=300, showlegend=False,
        yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor="#eee"),
        margin=dict(l=10, r=10, t=20, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_nova_chart(nova_all_med, nova_trad_med, nova_lsf_med, n_nova, n_trad, n_lsf, agent_psqm):
    fig = go.Figure()
    bars = [
        ("Construção nova (todas)", nova_all_med, n_nova, CHART_COLORS["muted"]),
        ("Nova — tradicional", nova_trad_med, n_trad, CHART_COLORS["ocean"]),
        ("Nova — LSF / indet.", nova_lsf_med, n_lsf, CHART_COLORS["terra"]),
    ]
    for label, med, n, color in bars:
        fig.add_trace(go.Bar(
            x=[label], y=[med], marker_color=color,
            text=[f"€{med:,.0f}/m² (n={n})".replace(",", ".")],
            textposition="outside", textfont=dict(size=11),
        ))
    fig.add_hline(y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["terra"], line_width=2,
                  annotation_text=f"Alvo: €{agent_psqm:,.0f}/m²".replace(",", "."),
                  annotation_font_color=CHART_COLORS["terra"], annotation_position="top right")
    fig.update_layout(
        height=320, showlegend=False,
        yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor="#eee"),
        margin=dict(l=10, r=10, t=20, b=60),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_importance_chart(importances):
    sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
    names = [FEAT_NAMES.get(f, f) for f, _ in reversed(sorted_imp)]
    vals = [v * 100 for _, v in reversed(sorted_imp)]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=names, x=vals, orientation="h",
        marker_color=CHART_COLORS["ocean"],
        text=[f"{v:.1f}%" for v in vals],
        textposition="outside", textfont=dict(size=11),
    ))
    fig.update_layout(
        height=380, showlegend=False,
        xaxis=dict(title="Importância no preço (%)", showgrid=True, gridcolor="#eee"),
        yaxis=dict(automargin=True),
        margin=dict(l=10, r=50, t=10, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


def build_scatter_chart(preds, agent_psqm):
    fig = go.Figure()
    market = preds[~preds["is_agent"]]
    fig.add_trace(go.Scatter(
        x=market["predicted"], y=market["price_per_sqm"],
        mode="markers",
        marker=dict(color=CHART_COLORS["ocean"], size=4, opacity=0.3),
        name="Mercado",
    ))
    agents = preds[preds["is_agent"]]
    fig.add_trace(go.Scatter(
        x=agents["predicted"], y=agents["price_per_sqm"],
        mode="markers",
        marker=dict(color=CHART_COLORS["terra"], size=12, line=dict(color="white", width=2)),
        name="Propriedades-alvo",
    ))
    max_val = min(preds[["predicted", "price_per_sqm"]].max().max() * 1.05, 15000)
    fig.add_trace(go.Scatter(
        x=[0, max_val], y=[0, max_val],
        mode="lines", line=dict(color="#ccc", width=1, dash="dash"),
        showlegend=False,
    ))
    fig.update_layout(
        height=400,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
        xaxis=dict(title="Previsão do modelo (€/m²)", showgrid=True, gridcolor="#f0f0f0", range=[0, max_val]),
        yaxis=dict(title="Preço real (€/m²)", showgrid=True, gridcolor="#f0f0f0", range=[0, max_val]),
        margin=dict(l=10, r=10, t=10, b=40),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------
def build_html(sections):
    css = """
    @page {
        size: A4;
        margin: 20mm 18mm 25mm 18mm;
        @bottom-center {
            content: "Waldyn Imobiliário · Análise de Mercado · Julho 2026 — pág. " counter(page) " de " counter(pages);
            font-size: 8pt;
            color: #999;
        }
    }
    * { box-sizing: border-box; }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        font-size: 10pt;
        line-height: 1.5;
        color: #1a1a2e;
        margin: 0;
        padding: 0;
    }
    h1 { font-size: 20pt; margin: 0 0 6pt 0; color: #1B5E8C; }
    h2 { font-size: 14pt; margin: 18pt 0 8pt 0; color: #1B5E8C; page-break-after: avoid; }
    h3 { font-size: 11pt; margin: 12pt 0 4pt 0; color: #333; page-break-after: avoid; }
    p { margin: 0 0 6pt 0; }
    .page-break { page-break-before: always; }
    .avoid-break { page-break-inside: avoid; }

    .subtitle { font-size: 11pt; color: #495057; margin-bottom: 12pt; }
    .metrics { display: flex; gap: 10px; margin: 10pt 0; }
    .metric-box {
        flex: 1;
        background: #f8f9fa;
        border-radius: 6px;
        padding: 10px 12px;
        border-left: 3px solid #1B5E8C;
    }
    .metric-box.agent { border-left-color: #C2703E; background: #fef3ec; }
    .metric-box .label { font-size: 7.5pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: #6c757d; }
    .metric-box .value { font-size: 16pt; font-weight: 700; color: #1a1a2e; }
    .metric-box .detail { font-size: 8pt; color: #6c757d; }

    .finding {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 6px;
        padding: 8pt 10pt;
        margin: 8pt 0;
        font-size: 9.5pt;
        line-height: 1.6;
    }
    .finding.info { background: #e8f4f8; border-color: #1B5E8C; }
    .finding.danger { background: #fde8e8; border-color: #B83D3D; }

    .chart-container { text-align: center; margin: 6pt 0; }
    .chart-container svg { max-width: 100%; height: auto; }

    table.comps {
        width: 100%;
        border-collapse: collapse;
        font-size: 7.5pt;
        margin: 8pt 0;
        table-layout: fixed;
    }
    table.comps col.col-title { width: 45%; }
    table.comps col.col-price { width: 15%; }
    table.comps col.col-psqm { width: 13%; }
    table.comps col.col-area { width: 12%; }
    table.comps col.col-tip { width: 15%; }
    table.comps th {
        background: #f0f2f6;
        padding: 3pt 5pt;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #dee2e6;
    }
    table.comps td {
        padding: 2.5pt 5pt;
        border-bottom: 1px solid #eee;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    table.comps td:first-child { white-space: normal; word-wrap: break-word; }
    table.comps tr.agent { background: #fde8d8; font-weight: 600; }

    .conclusions h3 { color: #1B5E8C; }
    .conclusions ul { margin: 2pt 0 6pt 0; padding-left: 14pt; }
    .conclusions li { margin-bottom: 2pt; }
    """

    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="utf-8">
<title>Análise de Mercado Imobiliário — Waldyn</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("Loading data...")
    df = load_data()

    print("Running regression...")
    regression = run_regression(df)
    comps = get_comparables(df)

    agent_df = df[df["is_agent"]]
    agent_price = agent_df["price_eur"].iloc[0]
    agent_area_lote = 552.0
    agent_area_construcao = 253.92
    agent_area_habitacao = 223.91
    agent_psqm = agent_df["price_per_sqm"].iloc[0]
    agent_rooms = int(agent_df["num_rooms"].iloc[0])

    # Percentiles
    pct_market = (df["price_per_sqm"] < agent_psqm).mean() * 100
    pct_comps_psqm = (comps["price_per_sqm"] < agent_psqm).mean() * 100
    pct_comps_abs = (comps["price_eur"] < agent_price).mean() * 100

    comps_t4 = comps[comps["num_rooms"] == 4]
    pct_comps_abs_t4 = (comps_t4["price_eur"] < agent_price).mean() * 100 if len(comps_t4) > 0 else 0

    comps_with_rooms = comps.dropna(subset=["num_rooms"])
    if len(comps_with_rooms) > 0:
        comps_with_rooms = comps_with_rooms.copy()
        comps_with_rooms["price_per_room"] = comps_with_rooms["price_eur"] / comps_with_rooms["num_rooms"]
        agent_ppr = agent_price / agent_rooms
        pct_per_room = (comps_with_rooms["price_per_room"] < agent_ppr).mean() * 100
    else:
        pct_per_room = 0

    comps_with_wc = comps.dropna(subset=["num_bathrooms"])
    if len(comps_with_wc) > 0:
        comps_with_wc = comps_with_wc.copy()
        comps_with_wc["price_per_wc"] = comps_with_wc["price_eur"] / comps_with_wc["num_bathrooms"]
        agent_nb = agent_df["num_bathrooms"].iloc[0]
        if pd.notna(agent_nb) and agent_nb > 0:
            agent_ppwc = agent_price / agent_nb
            pct_per_wc = (comps_with_wc["price_per_wc"] < agent_ppwc).mean() * 100
        else:
            pct_per_wc = 0
    else:
        pct_per_wc = 0

    # Condition stats
    cond_stats = df.groupby("condition", dropna=False).agg(
        n=("price_eur", "size"), median_price=("price_eur", "median"),
        median_psqm=("price_per_sqm", "median"), mean_area=("area_bruta_sqm", "mean"),
    ).reset_index()
    cond_stats = cond_stats.dropna(subset=["condition"])
    cond_stats = cond_stats.sort_values("median_psqm", ascending=False)
    COND_LABELS = {
        "Empreendimento de nova construção": "Construção nova",
        "Segunda mão/bom estado": "Bom estado",
        "Segunda mão/para recuperar": "Para recuperar",
    }
    cond_stats["label"] = cond_stats["condition"].map(COND_LABELS)

    # LSF stats
    lsf_stats = df.groupby("construction_type", observed=True).agg(
        n=("price_eur", "size"), median_price=("price_eur", "median"),
        median_psqm=("price_per_sqm", "median"), mean_area=("area_bruta_sqm", "mean"),
    ).reset_index()
    n_lsf = int(lsf_stats[lsf_stats["construction_type"] == "Provável LSF"]["n"].iloc[0])
    lsf_median = lsf_stats[lsf_stats["construction_type"] == "Provável LSF"]["median_psqm"].iloc[0]
    trad_median = lsf_stats[lsf_stats["construction_type"] == "Tradicional"]["median_psqm"].iloc[0]

    # Nova decomposition
    desc_col = df["description_full"].fillna("").str.lower()
    is_new_flag = (
        (df["condition"] == "Empreendimento de nova construção")
        | desc_col.str.contains("construção nova", regex=False)
    )
    nova_df = df[is_new_flag & ~df["is_agent"]].copy()
    nova_trad = nova_df[nova_df["construction_type"] == "Tradicional"]
    nova_lsf_indet = nova_df[nova_df["construction_type"].isin(["Provável LSF", "Indeterminado"])]
    nova_trad_med = nova_trad["price_per_sqm"].median() if len(nova_trad) > 0 else 0
    nova_lsf_med = nova_lsf_indet["price_per_sqm"].median() if len(nova_lsf_indet) > 0 else 0
    nova_all_med = nova_df["price_per_sqm"].median() if len(nova_df) > 0 else 0
    pct_above_lsf = ((agent_psqm - nova_lsf_med) / nova_lsf_med * 100) if nova_lsf_med > 0 else 0

    cond_nova_median = cond_stats[cond_stats["label"] == "Construção nova"]["median_psqm"].iloc[0]
    agent_dist_beach = df[df["is_agent"]]["dist_beach_km"].iloc[0]
    agent_dist_sintra = df[df["is_agent"]]["dist_sintra_km"].iloc[0]

    # -----------------------------------------------------------------------
    # Build sections
    # -----------------------------------------------------------------------
    sections = []

    # --- PAGE 1: Title + Key Numbers + Percentiles ---
    print("Building page 1: title, metrics, percentiles...")

    pct_chart_svg = fig_to_svg(build_percentile_chart([
        ("€/m² (habitação) — mercado total", pct_market),
        ("€/m² (habitação) — comparáveis 3km", pct_comps_psqm),
        ("Preço absoluto — comparáveis 3km", pct_comps_abs),
        ("Preço absoluto — T4 comparáveis", pct_comps_abs_t4),
        ("Preço por quarto", pct_per_room),
        ("Preço por casa de banho", pct_per_wc),
    ]), width=660, height=260)

    psqm_fmt = f"{agent_psqm:,.0f}".replace(",", ".")

    sections.append(f"""
    <h1>Estas casas são caras ou baratas?</h1>
    <p class="subtitle">
        Análise de {len(df)} imóveis à venda em Sintra/Cascais para avaliar o posicionamento
        de 3 propriedades-alvo (Century 21 Nações) no mercado.
    </p>

    <h2>Os números-chave</h2>
    <div class="metrics">
        <div class="metric-box agent">
            <div class="label">Preço pedido</div>
            <div class="value">{fmt_eur(agent_price)}</div>
            <div class="detail">3 moradias T{agent_rooms}</div>
        </div>
        <div class="metric-box">
            <div class="label">Lote</div>
            <div class="value">{agent_area_lote:.0f}m²</div>
            <div class="detail">Terreno total</div>
        </div>
        <div class="metric-box">
            <div class="label">Construção</div>
            <div class="value">{agent_area_construcao:.0f}m²</div>
            <div class="detail">Área bruta</div>
        </div>
        <div class="metric-box agent">
            <div class="label">Habitação</div>
            <div class="value">{agent_area_habitacao:.0f}m²</div>
            <div class="detail">€{psqm_fmt}/m²</div>
        </div>
    </div>

    <h2>Posição no mercado — todas as métricas</h2>
    <p>Cada barra mostra a posição das propriedades-alvo: acima de P50 é mais caro que a maioria.
    <span style="color:#B83D3D; font-weight:600">Vermelho</span> = acima da mediana;
    <span style="color:#2D7D5F; font-weight:600">verde</span> = abaixo.</p>
    <div class="chart-container">{pct_chart_svg}</div>

    <div class="finding info">
    <strong>Como ler:</strong> P50 = metade do mercado. Usando a área de habitação real ({agent_area_habitacao:.0f}m²),
    estas propriedades são <strong>mais caras que a maioria em todas as métricas</strong>.
    </div>
    """)

    # --- PAGE 2: Condition + LSF ---
    print("Building page 2: condition and LSF analysis...")
    cond_chart_svg = fig_to_svg(build_condition_chart(cond_stats, agent_psqm), width=660, height=280)
    lsf_chart_svg = fig_to_svg(build_lsf_chart(lsf_stats, agent_psqm), width=660, height=280)

    def n_fmt(v):
        return f"{v:,.0f}".replace(",", ".")

    sections.append(f"""
    <div class="page-break"></div>
    <h2>Análise por estado de conservação</h2>
    <div class="chart-container">{cond_chart_svg}</div>

    <div class="finding info">
    Com €{n_fmt(agent_psqm)}/m², o preço está alinhado com o segmento de <strong>construção nova</strong>
    (mediana €{n_fmt(cond_nova_median)}/m²), apesar de estarem classificadas como "bom estado" no Idealista.
    </div>

    <h2>Tipo de construção: LSF vs. Tradicional</h2>
    <p>Identificámos <strong>{n_lsf} prováveis LSF</strong> em {len(df)} imóveis via análise de texto.
    As propriedades-alvo são <strong>LSF confirmado</strong> pelo construtor.</p>
    <div class="chart-container">{lsf_chart_svg}</div>

    <div class="finding">
    <strong>LSF vs. Tradicional:</strong> Imóveis com provável construção LSF têm mediana de
    <strong>€{n_fmt(lsf_median)}/m²</strong> vs. <strong>€{n_fmt(trad_median)}/m²</strong> nos tradicionais.
    As propriedades-alvo (€{n_fmt(agent_psqm)}/m²) estão <strong>acima da mediana LSF</strong>.
    </div>
    """)

    # --- PAGE 3: Nova decomposition + Feature importance ---
    print("Building page 3: nova decomposition and feature importance...")
    nova_chart_svg = fig_to_svg(build_nova_chart(
        nova_all_med, nova_trad_med, nova_lsf_med,
        len(nova_df), len(nova_trad), len(nova_lsf_indet), agent_psqm
    ), width=660, height=290)
    imp_chart_svg = fig_to_svg(build_importance_chart(regression['importances']), width=660, height=340)

    sections.append(f"""
    <div class="page-break"></div>
    <h2>O argumento da construção nova — decomposto</h2>
    <div class="chart-container">{nova_chart_svg}</div>

    <div class="finding danger">
    <strong>O argumento "está abaixo da mediana de construção nova" é enganador.</strong>
    A mediana de construção nova (€{n_fmt(nova_all_med)}/m²) mistura betão/alvenaria
    (€{n_fmt(nova_trad_med)}/m²) com LSF (€{n_fmt(nova_lsf_med)}/m²). O construtor cobra
    €{n_fmt(agent_psqm)}/m² por construção LSF — <strong>{pct_above_lsf:.0f}% acima</strong>
    da mediana de construção nova LSF/indeterminada.
    </div>

    <h2>O que determina o preço de um imóvel?</h2>
    <p>Modelo Gradient Boosting (R²={regression['r2']*100:.0f}%) sobre {regression['n']} imóveis.</p>
    <div class="chart-container">{imp_chart_svg}</div>
    """)

    # --- PAGE 4: Scatter + Comparables ---
    print("Building page 4: scatter plot and comparables table...")
    scatter_svg = fig_to_svg(build_scatter_chart(regression['predictions'], agent_psqm), width=660, height=360)

    sections.append(f"""
    <div class="page-break"></div>
    <h2>Preço real vs. previsão do modelo</h2>
    <p>Acima da diagonal = sobrevalorizado. Os pontos <span style="color:#C2703E; font-weight:600">laranjas</span>
    são as propriedades-alvo.</p>
    <div class="chart-container">{scatter_svg}</div>
    """)

    if regression["agent_pred"]:
        diff_pct = (agent_psqm - regression["agent_pred"]) / regression["agent_pred"] * 100
        direction = "abaixo" if diff_pct < 0 else "acima"
        sections.append(f"""
        <div class="finding info">
        O modelo prevê <strong>€{n_fmt(regression['agent_pred'])}/m²</strong> para estas propriedades.
        O preço real é €{n_fmt(agent_psqm)}/m² — <strong>{abs(diff_pct):.1f}% {direction}</strong> do previsto.
        </div>
        """)

    # Comparables table
    comp_rows = ""
    for _, row in comps.iterrows():
        cls = ' class="agent"' if row["is_agent"] else ""
        comp_rows += f"""<tr{cls}>
            <td>{row['title'][:60]}</td>
            <td style="text-align:right">{fmt_eur(row['price_eur'])}</td>
            <td style="text-align:right">{fmt_eur(row['price_per_sqm'])}</td>
            <td style="text-align:right">{row['area_bruta_sqm']:.0f}</td>
            <td>{row['tipologia']}</td>
        </tr>\n"""

    sections.append(f"""
    <div class="page-break"></div>
    <h2>Propriedades comparáveis ({len(comps)} imóveis)</h2>
    <p>Raio 3km, T3–T5, bom estado, sem piscina. Linhas destacadas = propriedades-alvo.</p>
    <table class="comps">
    <colgroup>
        <col class="col-title"><col class="col-price"><col class="col-psqm">
        <col class="col-area"><col class="col-tip">
    </colgroup>
    <thead><tr><th>Imóvel</th><th>Preço</th><th>€/m²</th><th>Área (m²)</th><th>Tipologia</th></tr></thead>
    <tbody>
    {comp_rows}
    </tbody>
    </table>
    """)

    # --- PAGE 5: Conclusions ---
    print("Building page 5: conclusions...")
    pred_total = fmt_eur(regression['agent_pred'] * agent_area_habitacao)

    sections.append(f"""
    <div class="page-break"></div>
    <div class="conclusions">
    <h2>Conclusões — o que dizer ao cliente</h2>

    <h3>1. €{n_fmt(agent_psqm)}/m² de área habitável</h3>
    <p>Com {agent_area_habitacao:.0f}m² de habitação e preço de {fmt_eur(agent_price)},
    o custo por m² habitável é <strong>€{n_fmt(agent_psqm)}/m²</strong>.</p>

    <h3>2. Construção LSF — o elefante na sala</h3>
    <p>Construção LSF tem custo 15-25% inferior ao betão/alvenaria. A mediana LSF no mercado é
    <strong>€{n_fmt(lsf_median)}/m²</strong> vs. <strong>€{n_fmt(trad_median)}/m²</strong> nos tradicionais.
    O preço-alvo está acima da mediana LSF.</p>

    <h3>3. O argumento da "construção nova" não cola</h3>
    <p>A mediana geral de construção nova (€{n_fmt(cond_nova_median)}/m²) mistura betão com LSF.
    Quando se compara só com LSF/indeterminada, o construtor está <strong>{pct_above_lsf:.0f}% acima</strong>.</p>

    <h3>4. Comparando com imóveis semelhantes</h3>
    <p>Filtrando por comparáveis reais (3km, T3-T5, bom estado, sem piscina), estas propriedades são
    <strong>mais caras que {pct_comps_abs:.0f}%</strong> dos comparáveis em preço absoluto.</p>

    <h3>5. O que valoriza (e desvaloriza) estas casas</h3>
    <ul>
    <li><strong>A favor:</strong> Construção nova, acabamentos de qualidade, proximidade à praia (~{agent_dist_beach:.1f}km), T{agent_rooms}</li>
    <li><strong>Contra:</strong> Construção LSF (custo inferior), distância a Sintra (~{agent_dist_sintra:.1f}km)</li>
    </ul>

    <h3>6. O preço justo segundo o modelo</h3>
    <p>O modelo (R²={regression['r2']:.0%}) sugere <strong>€{n_fmt(regression['agent_pred'])}/m²</strong>,
    o que daria um preço total de ~{pred_total}.</p>
    </div>

    <div style="text-align: center; color: #999; font-size: 8pt; margin-top: 30pt; border-top: 1px solid #eee; padding-top: 10pt;">
        Waldyn Imobiliário · Análise de mercado baseada em {len(df)} imóveis · Dados Idealista · Julho 2026
    </div>
    """)

    # -----------------------------------------------------------------------
    # Render PDF
    # -----------------------------------------------------------------------
    print("Generating HTML...")
    html_content = build_html(sections)

    # Save HTML for debugging
    html_path = OUTPUT_PATH.with_suffix(".html")
    html_path.write_text(html_content, encoding="utf-8")
    print(f"HTML saved to: {html_path}")

    print("Converting to PDF...")
    HTML(string=html_content, base_url=str(DATA_DIR)).write_pdf(str(OUTPUT_PATH))
    print(f"PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
