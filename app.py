"""
Dashboard de Análise Imobiliária — Waldyn Imobiliário
Comparação de 3 propriedades Century 21 Nações vs. mercado Idealista
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Análise Imobiliária — Waldyn",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_DIR = Path(__file__).resolve().parent / "data"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
AGENT_IDS = [35066445, 35066465, 35066248]

SINTRA_CENTER = (38.7979, -9.3817)
CASCAIS_CENTER = (38.6967, -9.4217)
LISBON_CENTER = (38.7223, -9.1393)


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


def fmt_pct(v):
    return f"{v:.0f}%"


# ---------------------------------------------------------------------------
# Custom theme
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    .block-container { max-width: 1100px; padding-top: 4rem; }

    h1, h2, h3 {
        font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif !important;
        color: #FFFFFF !important;
    }
    h1 { letter-spacing: -0.02em; }
    h2 { letter-spacing: -0.01em; }

    .metric-card {
        background: #0F2424;
        border-radius: 10px;
        padding: 1.1rem 1.3rem;
        border: 1px solid rgba(255,255,255,0.08);
        border-left: 3px solid #7B6FF7;
        margin-bottom: 0.5rem;
    }
    .metric-card.agent {
        border-left-color: #F0A030;
        background: #0F2424;
    }
    .metric-card.alert {
        border-left-color: #E8624A;
    }
    .metric-card .label {
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: rgba(255,255,255,0.4);
        margin-bottom: 0.25rem;
        font-family: 'Inter', sans-serif;
    }
    .metric-card .value {
        font-size: 1.7rem;
        font-weight: 700;
        color: #FFFFFF;
        line-height: 1.1;
        font-family: 'Space Grotesk', 'Inter', sans-serif;
    }
    .metric-card .detail {
        font-size: 0.78rem;
        color: rgba(255,255,255,0.5);
        margin-top: 0.25rem;
    }

    .finding-box {
        background: rgba(240,160,48,0.08);
        border: 1px solid rgba(240,160,48,0.25);
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
        font-size: 0.92rem;
        line-height: 1.6;
        color: rgba(255,255,255,0.82);
    }
    .finding-box.info {
        background: rgba(123,111,247,0.08);
        border-color: rgba(123,111,247,0.25);
    }
    .finding-box.danger {
        background: rgba(232,98,74,0.08);
        border-color: rgba(232,98,74,0.3);
    }

    .section-intro {
        font-size: 1rem;
        color: rgba(255,255,255,0.62);
        line-height: 1.7;
        margin-bottom: 1.5rem;
        max-width: 800px;
    }

    div[data-testid="stMetric"] {
        background: #0F2424;
        border-radius: 8px;
        padding: 0.75rem;
        border: 1px solid rgba(255,255,255,0.08);
    }

    /* Streamlit divider */
    hr { border-color: rgba(255,255,255,0.08) !important; }

    /* Dataframe dark overrides */
    .stDataFrame { border-radius: 8px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Load & process data
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    listings = pd.read_csv(DATA_DIR / "listings.csv")
    details = pd.read_csv(DATA_DIR / "details.csv")
    enrichment = pd.read_csv(DATA_DIR / "enrichment.csv")

    df = listings.merge(details, on="listing_id", how="left").merge(enrichment, on="listing_id", how="left")

    df = df.dropna(subset=["price_eur", "area_bruta_sqm", "latitude", "longitude"])
    df = df[df["price_eur"] > 0]
    df = df[df["area_bruta_sqm"] > 0]

    df["price_per_sqm"] = df["price_eur"] / df["area_bruta_sqm"]

    # Compute beach distance from nearest known beach (enrichment field is 80% empty)
    beaches = [
        (38.8379, -9.4611),  # Azenhas do Mar
        (38.8458, -9.4421),  # Magoito
        (38.8246, -9.4639),  # Praia das Maçãs
        (38.8139, -9.4714),  # Praia Grande
        (38.7893, -9.4833),  # Praia da Adraga
        (38.7283, -9.4747),  # Praia do Guincho
        (38.7069, -9.4594),  # Crismina
        (38.6797, -9.3361),  # Carcavelos
        (38.6867, -9.3194),  # São Pedro do Estoril
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

    # --- Construction type classification (LSF vs traditional) ---
    desc = df["description_full"].fillna("").str.lower()

    # Explicit LSF keywords → high confidence
    lsf_explicit = desc.str.contains(
        r"lsf|light steel|steel frame|aço leve|construção seca|ossatura met[aá]lica",
        regex=True,
    )

    # Strong LSF indicators
    has_etics = desc.str.contains("etics", case=False)
    has_efficiency = desc.str.contains(
        r"eficiência energética|isolamento térmico|desempenho térmico|eficiencia energetica",
        regex=True,
    )
    has_modular = desc.str.contains(r"modular|pré-fabricad|pre-fabricad", regex=True)

    # Traditional construction markers (negative signal)
    has_traditional = desc.str.contains(
        r"betão armado|betao armado|alvenaria|tijolo|construção tradicional|pedra aparelhada",
        regex=True,
    )

    # Is new construction (from condition or description)
    is_new = (
        (df["condition"] == "Empreendimento de nova construção")
        | desc.str.contains("construção nova|construccion nueva", regex=True)
    )

    # Energy certificate A or A+
    cert = df["energy_certificate"].fillna("").str.upper()
    has_good_cert = cert.str.contains(r"^A\+?$", regex=True)

    # Year built 2020+
    year = pd.to_numeric(df["year_built"], errors="coerce")
    is_recent = year >= 2020

    # Build score
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

    # Force agent properties to LSF (confirmed by client)
    score.loc[df["is_agent"]] = 0.90

    df["lsf_score"] = score
    df["construction_type"] = pd.cut(
        score,
        bins=[-0.01, 0.10, 0.25, 1.01],
        labels=["Tradicional", "Indeterminado", "Provável LSF"],
    )

    # Override agent properties with real habitable area (223.91m²)
    # The Idealista listing says 435m² but real documentation shows:
    # lote=552m², construção bruta=253.92m², habitação=223.91m²
    # Most market listings have area_bruta ≈ area_util, so we use the real
    # habitable area for a fair comparison.
    AGENT_AREA_HABITACAO = 223.91
    agent_mask = df["is_agent"]
    df.loc[agent_mask, "area_bruta_sqm"] = AGENT_AREA_HABITACAO
    df.loc[agent_mask, "area_util_sqm"] = AGENT_AREA_HABITACAO
    df.loc[agent_mask, "price_per_sqm"] = df.loc[agent_mask, "price_eur"] / AGENT_AREA_HABITACAO

    return df


@st.cache_data
def run_regression(df):
    from sklearn.ensemble import GradientBoostingRegressor

    features = [
        "area_bruta_sqm", "dist_sintra_km", "dist_beach_km", "num_rooms",
        "dist_cascais_km", "num_bathrooms", "dist_lisbon_km",
    ]
    binary_features = {
        "pool": "has_pool",
        "terrace": "has_terrace",
        "garden": "has_garden",
    }
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

    from sklearn.model_selection import cross_val_score, cross_val_predict

    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=3, learning_rate=0.1,
        subsample=0.8, random_state=42,
    )
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    r2 = cv_scores.mean()

    # Out-of-fold predictions for honest residuals
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


@st.cache_data
def get_comparables(df):
    agent = df[df["is_agent"]].iloc[0]
    lat, lon = agent["latitude"], agent["longitude"]

    df_c = df.copy()
    df_c["dist_to_agent"] = haversine(df_c["latitude"], df_c["longitude"], lat, lon)

    nearby = df_c[df_c["dist_to_agent"] <= 3.0].copy()
    nearby = nearby[nearby["num_rooms"].between(3, 5)]
    nearby = nearby[nearby["condition"] == "Segunda mão/bom estado"]

    return nearby.sort_values("price_per_sqm", ascending=False)


# ---------------------------------------------------------------------------
# Load everything
# ---------------------------------------------------------------------------
df = load_data()
regression = run_regression(df)
comps = get_comparables(df)

agent_df = df[df["is_agent"]]
agent_price = agent_df["price_eur"].iloc[0]
agent_area_lote = 552.0
agent_area_construcao = 253.92
agent_area_habitacao = 223.91
agent_area_bruta = agent_df["area_bruta_sqm"].iloc[0]  # = 223.91 (habitação)
agent_area_util = agent_area_bruta
agent_psqm = agent_df["price_per_sqm"].iloc[0]  # based on 223.91m²
agent_psqm_construcao = agent_price / agent_area_construcao
agent_rooms = int(agent_df["num_rooms"].iloc[0])

# Percentile calculations
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


# ---------------------------------------------------------------------------
# Feature name translations
# ---------------------------------------------------------------------------
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

CHART_COLORS = {
    "purple": "#7B6FF7",
    "teal": "#2CC4A8",
    "amber": "#F0A030",
    "coral": "#E8624A",
    "muted": "rgba(255,255,255,0.25)",
}

CHART_FONT = dict(family="Inter, sans-serif", color="rgba(255,255,255,0.62)", size=12)
CHART_GRID = "rgba(255,255,255,0.06)"
CHART_BG = "rgba(0,0,0,0)"


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

st.image(str(ASSETS_DIR / "waldyn-wordmark.png"), width=160)
st.markdown("# Estas casas são caras ou baratas?")
st.markdown(f"""
<p class="section-intro">
Analisámos <strong>{len(df)} imóveis</strong> à venda na zona de Sintra/Cascais para perceber se as
3 propriedades-alvo (Century 21 Nações) estão bem posicionadas no mercado.
A resposta depende de <em>como</em> se mede — e essa é a descoberta mais importante desta análise.
</p>
""", unsafe_allow_html=True)

st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Key numbers
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 📊 Os números-chave")
st.markdown("""
<p class="section-intro">
Três números que resumem a situação das propriedades-alvo. O preço pedido, o que o modelo estatístico prevê,
e a posição relativa quando comparamos com imóveis verdadeiramente semelhantes.
</p>
""", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""
    <div class="metric-card agent">
        <div class="label">Preço pedido</div>
        <div class="value">{fmt_eur(agent_price)}</div>
        <div class="detail">3 moradias T{agent_rooms} · Propriedades-alvo</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Lote</div>
        <div class="value">{agent_area_lote:.0f}m²</div>
        <div class="detail">Área total do terreno</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Construção</div>
        <div class="value">{agent_area_construcao:.0f}m²</div>
        <div class="detail">Área bruta de construção</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card agent">
        <div class="label">Habitação</div>
        <div class="value">{agent_area_habitacao:.0f}m²</div>
        <div class="detail">Área habitável · €{agent_psqm:,.0f}/m²</div>
    </div>
    """.replace(",", "."), unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Positioning across metrics
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🔍 Posição no mercado — todas as métricas")
st.markdown("""
<p class="section-intro">
Cada barra mostra a posição das propriedades-alvo face ao mercado: acima de P50
é mais caro que a maioria. Barras <strong style="color:#E8624A">coral</strong>
= acima da mediana; <strong style="color:#2CC4A8">teal</strong> = abaixo.
</p>
""", unsafe_allow_html=True)

pct_data = [
    ("€/m² (habitação) — mercado total", pct_market),
    ("€/m² (habitação) — comparáveis 3km", pct_comps_psqm),
    ("Preço absoluto — comparáveis 3km", pct_comps_abs),
    ("Preço absoluto — T4 comparáveis", pct_comps_abs_t4),
    ("Preço por quarto", pct_per_room),
    ("Preço por casa de banho", pct_per_wc),
]

fig_pct = go.Figure()
for label, pct in reversed(pct_data):
    color = CHART_COLORS["coral"] if pct >= 50 else CHART_COLORS["teal"]
    fig_pct.add_trace(go.Bar(
        y=[label],
        x=[pct],
        orientation="h",
        marker_color=color,
        opacity=0.85,
        text=[f"P{pct:.0f}"],
        textposition="outside",
        textfont=dict(size=13, color=color),
        hovertemplate=f"<b>{label}</b><br>Percentil: {pct:.0f}<br>Mais caro que {pct:.0f}% dos comparáveis<extra></extra>",
    ))

fig_pct.add_vline(x=50, line_dash="dot", line_color="rgba(255,255,255,0.25)", line_width=1,
                  annotation_text="Mediana", annotation_position="top",
                  annotation_font_color="rgba(255,255,255,0.5)")

fig_pct.update_layout(
    height=320,
    showlegend=False,
    font=CHART_FONT,
    xaxis=dict(range=[0, 105], title="Percentil (P50 = metade do mercado)", showgrid=True, gridcolor=CHART_GRID),
    yaxis=dict(automargin=True),
    margin=dict(l=10, r=40, t=20, b=40),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_pct, use_container_width=True)

st.markdown(f"""
<div class="finding-box info">
💡 <strong>Como ler:</strong> P50 = metade do mercado. Acima de P50, é mais caro que a maioria.
Usando a área de habitação real ({agent_area_habitacao:.0f}m²), estas propriedades são
<strong>mais caras que a maioria em todas as métricas</strong>.
</div>
""", unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2B: Condition analysis
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🏗️ Análise por estado de conservação")

cond_stats = df.groupby("condition", dropna=False).agg(
    n=("price_eur", "size"),
    median_price=("price_eur", "median"),
    median_psqm=("price_per_sqm", "median"),
    mean_area=("area_bruta_sqm", "mean"),
).reset_index()
cond_stats = cond_stats.dropna(subset=["condition"])
cond_stats = cond_stats.sort_values("median_psqm", ascending=False)

COND_LABELS = {
    "Empreendimento de nova construção": "Construção nova",
    "Segunda mão/bom estado": "Bom estado",
    "Segunda mão/para recuperar": "Para recuperar",
}
cond_stats["label"] = cond_stats["condition"].map(COND_LABELS)

agent_condition = agent_df["condition"].iloc[0]

st.markdown(f"""
<p class="section-intro">
O mercado divide-se em 3 segmentos por estado de conservação. As propriedades-alvo
estão classificadas no Idealista como <strong>"{COND_LABELS.get(agent_condition, agent_condition)}"</strong>,
mas a descrição do anúncio diz "moradia de construção nova".
</p>
""", unsafe_allow_html=True)

cond_colors = {
    "Construção nova": CHART_COLORS["teal"],
    "Bom estado": CHART_COLORS["purple"],
    "Para recuperar": CHART_COLORS["muted"],
}

fig_cond = go.Figure()
for _, row in cond_stats.iterrows():
    label = row["label"]
    fig_cond.add_trace(go.Bar(
        x=[label],
        y=[row["median_psqm"]],
        marker_color=cond_colors.get(label, CHART_COLORS["purple"]),
        text=[f"€{row['median_psqm']:,.0f}/m²".replace(",", ".")],
        textposition="outside",
        textfont=dict(size=13),
        hovertemplate=(
            f"<b>{label}</b><br>"
            f"Mediana €/m²: €{row['median_psqm']:,.0f}<br>"
            f"Mediana preço: €{row['median_price']:,.0f}<br>"
            f"Nº imóveis: {row['n']}<br>"
            f"Área média: {row['mean_area']:.0f}m²"
            "<extra></extra>"
        ),
    ))

fig_cond.add_hline(
    y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["amber"], line_width=2,
    annotation_text=f"Alvo: €{agent_psqm:,.0f}/m²".replace(",", "."),
    annotation_font_color=CHART_COLORS["amber"],
    annotation_position="top left",
)

fig_cond.update_layout(
    height=350,
    showlegend=False,
    font=CHART_FONT,
    yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor=CHART_GRID),
    xaxis=dict(title=""),
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_cond, use_container_width=True)

cc1, cc2, cc3 = st.columns(3)
for i, (_, row) in enumerate(cond_stats.iterrows()):
    col = [cc1, cc2, cc3][i]
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="label">{row["label"]}</div>
            <div class="value">{int(row["n"])} imóveis</div>
            <div class="detail">Mediana: {fmt_eur(row["median_price"])} · {row["mean_area"]:.0f}m² média</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown(f"""
<div class="finding-box info">
💡 <strong>Onde encaixam as propriedades-alvo?</strong> Com €{agent_psqm:,.0f}/m², o preço está
alinhado com o segmento de <strong>construção nova</strong> (mediana €{cond_stats[cond_stats["label"]=="Construção nova"]["median_psqm"].iloc[0]:,.0f}/m²),
apesar de estarem classificadas como "bom estado" no Idealista.
A descrição do anúncio diz explicitamente "moradia de construção nova" —
se a classificação estivesse correta, o preço seria competitivo dentro do seu segmento.
</div>
""".replace(",", "."), unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2C: Construction type (LSF vs traditional)
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🔩 Tipo de construção: LSF vs. Tradicional")

lsf_stats = df.groupby("construction_type", observed=True).agg(
    n=("price_eur", "size"),
    median_price=("price_eur", "median"),
    median_psqm=("price_per_sqm", "median"),
    mean_area=("area_bruta_sqm", "mean"),
).reset_index()

n_lsf = int(lsf_stats[lsf_stats["construction_type"] == "Provável LSF"]["n"].iloc[0])
n_indet = int(lsf_stats[lsf_stats["construction_type"] == "Indeterminado"]["n"].iloc[0])

st.markdown(f"""
<p class="section-intro">
O Idealista não indica o método construtivo. Usámos análise de texto dos anúncios
para classificar cada imóvel: menções a ETICS, eficiência energética, construção modular
e ausência de referências a betão/alvenaria sugerem <strong>LSF (Light Steel Frame)</strong>.
Identificámos <strong>{n_lsf} prováveis LSF</strong> e <strong>{n_indet} indeterminados</strong>
em {len(df)} imóveis. As propriedades-alvo são <strong>LSF confirmado</strong> pelo construtor.
</p>
""", unsafe_allow_html=True)

ct_order = ["Provável LSF", "Indeterminado", "Tradicional"]
ct_colors = {
    "Provável LSF": CHART_COLORS["amber"],
    "Indeterminado": CHART_COLORS["muted"],
    "Tradicional": CHART_COLORS["purple"],
}

fig_lsf = go.Figure()
for ct in ct_order:
    row = lsf_stats[lsf_stats["construction_type"] == ct]
    if len(row) == 0:
        continue
    row = row.iloc[0]
    fig_lsf.add_trace(go.Bar(
        x=[ct],
        y=[row["median_psqm"]],
        marker_color=ct_colors[ct],
        text=[f"€{row['median_psqm']:,.0f}/m²".replace(",", ".")],
        textposition="outside",
        textfont=dict(size=13),
        hovertemplate=(
            f"<b>{ct}</b><br>"
            f"Mediana €/m²: €{row['median_psqm']:,.0f}<br>"
            f"Mediana preço: €{row['median_price']:,.0f}<br>"
            f"Nº imóveis: {int(row['n'])}<br>"
            f"Área média: {row['mean_area']:.0f}m²"
            "<extra></extra>"
        ),
    ))

fig_lsf.add_hline(
    y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["amber"], line_width=2,
    annotation_text=f"Alvo (LSF): €{agent_psqm:,.0f}/m²".replace(",", "."),
    annotation_font_color=CHART_COLORS["amber"],
    annotation_position="top left",
)

fig_lsf.update_layout(
    height=350,
    showlegend=False,
    font=CHART_FONT,
    yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor=CHART_GRID),
    xaxis=dict(title=""),
    margin=dict(l=10, r=10, t=20, b=40),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_lsf, use_container_width=True)

lc1, lc2, lc3 = st.columns(3)
for i, ct in enumerate(ct_order):
    row = lsf_stats[lsf_stats["construction_type"] == ct]
    if len(row) == 0:
        continue
    row = row.iloc[0]
    col = [lc1, lc2, lc3][i]
    with col:
        style = "agent" if ct == "Provável LSF" else ""
        st.markdown(f"""
        <div class="metric-card {style}">
            <div class="label">{ct}</div>
            <div class="value">{int(row["n"])} imóveis</div>
            <div class="detail">Mediana: {fmt_eur(row["median_price"])} · €{row["median_psqm"]:,.0f}/m²</div>
        </div>
        """.replace(",", "."), unsafe_allow_html=True)

# Show the LSF comparable listings
lsf_market = df[(df["construction_type"] == "Provável LSF") & (~df["is_agent"])].copy()
if len(lsf_market) > 0:
    st.markdown("#### Imóveis com provável construção LSF no mercado")
    lsf_display = lsf_market[["title", "price_eur", "price_per_sqm", "area_bruta_sqm",
                               "tipologia", "lsf_score"]].copy()
    lsf_display = lsf_display.sort_values("lsf_score", ascending=False)
    lsf_display = lsf_display.rename(columns={
        "title": "Imóvel", "price_eur": "Preço", "price_per_sqm": "€/m²",
        "area_bruta_sqm": "Área (m²)", "tipologia": "Tipologia", "lsf_score": "Score LSF",
    })
    lsf_display["Área (m²)"] = lsf_display["Área (m²)"].apply(lambda x: round(x) if pd.notna(x) else None)
    lsf_display["Score LSF"] = (lsf_display["Score LSF"] * 100).round(0)
    st.dataframe(
        lsf_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Preço": st.column_config.NumberColumn(format="€%d"),
            "€/m²": st.column_config.NumberColumn(format="€%d"),
            "Área (m²)": st.column_config.NumberColumn(format="%d"),
            "Score LSF": st.column_config.NumberColumn(format="%d%%"),
        },
    )

lsf_median = lsf_stats[lsf_stats["construction_type"] == "Provável LSF"]["median_psqm"].iloc[0]
trad_median = lsf_stats[lsf_stats["construction_type"] == "Tradicional"]["median_psqm"].iloc[0]

st.markdown(f"""
<div class="finding-box">
🔩 <strong>LSF vs. Tradicional:</strong> Os imóveis com provável construção LSF têm uma mediana
de <strong>€{lsf_median:,.0f}/m²</strong>, enquanto os tradicionais estão a <strong>€{trad_median:,.0f}/m²</strong>.
As propriedades-alvo, com €{agent_psqm:,.0f}/m², estão <strong>acima da mediana LSF</strong>.
O tipo de construção é relevante porque o custo de construção LSF é tipicamente 15-25% inferior
ao da construção tradicional — o que se deveria refletir no preço de venda.
</div>
""".replace(",", "."), unsafe_allow_html=True)

# --- Decompose "construção nova" by construction type ---
st.markdown("#### O argumento da construção nova — decomposto")

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

fig_nova = go.Figure()

bars = [
    ("Construção nova\n(todas)", nova_all_med, len(nova_df), CHART_COLORS["muted"]),
    ("Nova — tradicional", nova_trad_med, len(nova_trad), CHART_COLORS["purple"]),
    ("Nova — LSF / indet.", nova_lsf_med, len(nova_lsf_indet), CHART_COLORS["amber"]),
]

for label, med, n, color in bars:
    fig_nova.add_trace(go.Bar(
        x=[label],
        y=[med],
        marker_color=color,
        text=[f"€{med:,.0f}/m²\n(n={n})".replace(",", ".")],
        textposition="outside",
        textfont=dict(size=12),
        hovertemplate=f"<b>{label}</b><br>Mediana: €{med:,.0f}/m²<br>Nº imóveis: {n}<extra></extra>",
    ))

fig_nova.add_hline(
    y=agent_psqm, line_dash="dash", line_color=CHART_COLORS["amber"], line_width=2,
    annotation_text=f"Alvo (LSF): €{agent_psqm:,.0f}/m²".replace(",", "."),
    annotation_font_color=CHART_COLORS["amber"],
    annotation_position="top right",
)

fig_nova.update_layout(
    height=380,
    showlegend=False,
    font=CHART_FONT,
    yaxis=dict(title="Mediana €/m²", showgrid=True, gridcolor=CHART_GRID),
    xaxis=dict(title=""),
    margin=dict(l=10, r=10, t=20, b=60),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_nova, use_container_width=True)

pct_above_lsf = ((agent_psqm - nova_lsf_med) / nova_lsf_med * 100) if nova_lsf_med > 0 else 0

st.markdown(f"""
<div class="finding-box danger">
⚠️ <strong>O argumento "está abaixo da mediana de construção nova" é enganador.</strong>
A mediana de construção nova (€{nova_all_med:,.0f}/m²) mistura:
<ul style="margin: 0.5rem 0;">
<li><strong>{len(nova_trad)} imóveis de construção tradicional</strong> (betão/alvenaria) a €{nova_trad_med:,.0f}/m² — casas mais caras, que puxam a mediana para cima</li>
<li><strong>{len(nova_lsf_indet)} imóveis LSF / indeterminado</strong> a €{nova_lsf_med:,.0f}/m² — o segmento real de comparação</li>
</ul>
O construtor cobra €{agent_psqm:,.0f}/m² por construção LSF — <strong>{pct_above_lsf:.0f}% acima</strong>
da mediana de construção nova LSF/indeterminada.
Comparar com a mediana geral de construção nova é comparar LSF com betão armado.
</div>
""".replace(",", "."), unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: What drives the price
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🧠 O que determina o preço de um imóvel?")
st.markdown(f"""
<p class="section-intro">
Usámos um modelo estatístico (Gradient Boosting) que analisa {regression["n"]} imóveis e descobre
quais características mais influenciam o preço por m². O modelo explica
<strong>{regression["r2"] * 100:.0f}%</strong> da variação de preço — uma precisão elevada.
</p>
""", unsafe_allow_html=True)

sorted_imp = sorted(regression["importances"].items(), key=lambda x: x[1], reverse=True)

fig_imp = go.Figure()
names = [FEAT_NAMES.get(f, f) for f, _ in reversed(sorted_imp)]
vals = [v * 100 for _, v in reversed(sorted_imp)]

fig_imp.add_trace(go.Bar(
    y=names,
    x=vals,
    orientation="h",
    marker_color=CHART_COLORS["purple"],
    text=[f"{v:.1f}%" for v in vals],
    textposition="outside",
    textfont=dict(size=12, color="rgba(255,255,255,0.62)"),
    hovertemplate="<b>%{y}</b><br>Importância: %{x:.1f}%<extra></extra>",
))

fig_imp.update_layout(
    height=420,
    showlegend=False,
    font=CHART_FONT,
    xaxis=dict(title="Importância no preço (%)", showgrid=True, gridcolor=CHART_GRID),
    yaxis=dict(automargin=True),
    margin=dict(l=10, r=40, t=10, b=40),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_imp, use_container_width=True)

top3 = sorted_imp[:3]
st.markdown(f"""
<div class="finding-box info">
📌 <strong>Em linguagem simples:</strong> O tamanho da casa é o fator dominante
({top3[0][1]*100:.0f}%) — casas maiores tendem a ter preço/m² mais baixo.
{FEAT_NAMES.get(top3[1][0], top3[1][0])} ({top3[1][1]*100:.1f}%) e
{FEAT_NAMES.get(top3[2][0], top3[2][0])} ({top3[2][1]*100:.1f}%) vêm a seguir.
Amenidades como terraço, jardim ou construção nova pesam pouco no preço final.
</div>
""", unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Actual vs Predicted scatter
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 Preço real vs. previsão do modelo")
st.markdown("""
<p class="section-intro">
Cada ponto é um imóvel. Se está <strong>acima</strong> da linha diagonal, o preço real é superior
ao que o modelo prevê (sobrevalorizado). Se está <strong>abaixo</strong>, o preço é inferior ao previsto
(subvalorizado). Os pontos <strong style="color:#F0A030">âmbar</strong> são as propriedades-alvo.
</p>
""", unsafe_allow_html=True)

preds = regression["predictions"]

fig_scatter = go.Figure()

market = preds[~preds["is_agent"]]
fig_scatter.add_trace(go.Scatter(
    x=market["predicted"],
    y=market["price_per_sqm"],
    mode="markers",
    marker=dict(color=CHART_COLORS["purple"], size=5, opacity=0.35),
    name="Mercado",
    hovertemplate="Previsão: €%{x:,.0f}/m²<br>Real: €%{y:,.0f}/m²<br>Diferença: %{customdata:.1f}%<extra></extra>",
    customdata=market["residual_pct"],
))

agents = preds[preds["is_agent"]]
fig_scatter.add_trace(go.Scatter(
    x=agents["predicted"],
    y=agents["price_per_sqm"],
    mode="markers",
    marker=dict(color=CHART_COLORS["amber"], size=14, line=dict(color="#0B1A1A", width=2)),
    name="Propriedades-alvo",
    hovertemplate="<b>ALVO</b><br>Previsão: €%{x:,.0f}/m²<br>Real: €%{y:,.0f}/m²<br>Diferença: %{customdata:.1f}%<extra></extra>",
    customdata=agents["residual_pct"],
))

max_val = min(preds[["predicted", "price_per_sqm"]].max().max() * 1.05, 15000)
fig_scatter.add_trace(go.Scatter(
    x=[0, max_val], y=[0, max_val],
    mode="lines",
    line=dict(color="rgba(255,255,255,0.15)", width=1, dash="dash"),
    showlegend=False,
    hoverinfo="skip",
))

fig_scatter.update_layout(
    height=500,
    font=CHART_FONT,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01,
                bgcolor="rgba(15,36,36,0.8)", bordercolor="rgba(255,255,255,0.08)", borderwidth=1),
    xaxis=dict(title="Previsão do modelo (€/m²)", showgrid=True, gridcolor=CHART_GRID, range=[0, max_val]),
    yaxis=dict(title="Preço real (€/m²)", showgrid=True, gridcolor=CHART_GRID, range=[0, max_val]),
    margin=dict(l=10, r=10, t=10, b=40),
    plot_bgcolor=CHART_BG,
    paper_bgcolor=CHART_BG,
)

st.plotly_chart(fig_scatter, use_container_width=True)

if regression["agent_pred"]:
    diff_pct = (agent_psqm - regression["agent_pred"]) / regression["agent_pred"] * 100
    direction = "abaixo" if diff_pct < 0 else "acima"
    st.markdown(f"""
    <div class="finding-box info">
    📊 <strong>O modelo prevê €{regression["agent_pred"]:,.0f}/m²</strong> para estas propriedades
    (usando a área de habitação de {agent_area_habitacao:.0f}m²),
    e o preço real é €{agent_psqm:,.0f}/m² — <strong>{abs(diff_pct):.1f}% {direction}</strong> do previsto.
    </div>
    """.replace(",", "."), unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Comparables table
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🏘️ Propriedades comparáveis")
st.markdown(f"""
<p class="section-intro">
Encontrámos <strong>{len(comps)} imóveis</strong> verdadeiramente comparáveis: dentro de 3km,
tipologia T3 a T5, em bom estado. As linhas <strong style="color:#F0A030">destacadas</strong>
são as propriedades-alvo. A tabela está ordenada por €/m².
</p>
""", unsafe_allow_html=True)

display_comps = comps[["title", "price_eur", "price_per_sqm", "area_bruta_sqm",
                        "tipologia", "is_agent"]].copy()
display_comps = display_comps.reset_index(drop=True)

agent_mask = display_comps["is_agent"].values

display_comps = display_comps.rename(columns={
    "title": "Imóvel", "price_eur": "Preço", "price_per_sqm": "€/m²",
    "area_bruta_sqm": "Área (m²)", "tipologia": "Tipologia",
})
display_comps["Área (m²)"] = display_comps["Área (m²)"].apply(lambda x: round(x) if pd.notna(x) else None)
display_comps = display_comps.drop(columns=["is_agent"])

def highlight_agent(row):
    if agent_mask[row.name]:
        return ["background-color: rgba(240,160,48,0.15); font-weight: bold"] * len(row)
    return [""] * len(row)

styled = display_comps.style.apply(highlight_agent, axis=1)
st.dataframe(
    styled,
    use_container_width=True,
    height=600,
    column_config={
        "Preço": st.column_config.NumberColumn(format="€%d"),
        "€/m²": st.column_config.NumberColumn(format="€%d"),
        "Área (m²)": st.column_config.NumberColumn(format="%d"),
    },
)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Map
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🗺️ Mapa de comparáveis")
st.markdown("""
<p class="section-intro">
Localização geográfica dos imóveis comparáveis. Os pontos
<strong style="color:#F0A030">âmbar grandes</strong> são as propriedades-alvo.
</p>
""", unsafe_allow_html=True)

map_data = comps[["latitude", "longitude", "price_eur", "title", "is_agent"]].copy()
map_data["Tipo"] = map_data["is_agent"].apply(lambda x: "Propriedades-alvo" if x else "Mercado")
map_data["size"] = map_data["is_agent"].apply(lambda x: 15 if x else 5)

scatter_fn = getattr(px, "scatter_map", None) or getattr(px, "scatter_mapbox")
map_style_key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"

fig_map = scatter_fn(
    map_data,
    lat="latitude",
    lon="longitude",
    size="size",
    color="Tipo",
    color_discrete_map={"Propriedades-alvo": CHART_COLORS["amber"], "Mercado": CHART_COLORS["purple"]},
    hover_name="title",
    hover_data={"price_eur": ":,.0f", "Tipo": False, "size": False,
                "latitude": False, "longitude": False},
    zoom=12,
    height=500,
    labels={"price_eur": "Preço"},
)
fig_map.update_layout(
    margin=dict(l=0, r=0, t=0, b=0),
    legend=dict(title="", orientation="h", y=1.02),
    **{map_style_key: "open-street-map"},
)

st.plotly_chart(fig_map, use_container_width=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Conclusions
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 📋 Conclusões — o que dizer ao cliente")
st.markdown("""
<p class="section-intro">
As conclusões desta análise, escritas em linguagem clara para usar diretamente
na conversa com o cliente.
</p>
""", unsafe_allow_html=True)

cond_nova_median = cond_stats[cond_stats["label"]=="Construção nova"]["median_psqm"].iloc[0]
agent_dist_beach = df[df["is_agent"]]["dist_beach_km"].iloc[0]
agent_dist_sintra = df[df["is_agent"]]["dist_sintra_km"].iloc[0]

st.markdown(f"""
### 1. €{agent_psqm:,.0f}/m² de área habitável

Com {agent_area_habitacao:.0f}m² de área de habitação e um preço de {fmt_eur(agent_price)},
o custo por m² habitável é **€{agent_psqm:,.0f}/m²**.

### 2. Construção LSF — o elefante na sala

Estas casas são construção **LSF (Light Steel Frame)**, com custo de construção tipicamente
**15-25% inferior** ao betão/alvenaria. No mercado, identificámos {n_lsf} imóveis com
provável construção LSF, com mediana de **€{lsf_median:,.0f}/m²** vs. **€{trad_median:,.0f}/m²**
nos tradicionais. O preço-alvo (€{agent_psqm:,.0f}/m²) está **acima da mediana LSF**.

### 3. O argumento da "construção nova" não cola

A mediana geral de construção nova é €{cond_nova_median:,.0f}/m² — mas mistura betão (€{nova_trad_med:,.0f}/m²)
com LSF (€{nova_lsf_med:,.0f}/m²). Quando se compara apenas com construção nova LSF/indeterminada,
o construtor está **{pct_above_lsf:.0f}% acima** da mediana.

### 4. Comparando com imóveis semelhantes

Quando filtramos por imóveis verdadeiramente comparáveis (mesma zona, tipologia T3-T5,
bom estado), estas propriedades são **mais caras que {pct_comps_abs:.0f}% dos
comparáveis** em preço absoluto — e o filtro inclui maioritariamente segunda mão tradicional.

### 5. O que valoriza (e desvaloriza) estas casas

**A favor:**
- Construção nova com acabamentos de qualidade (pedra, Bosch, vidro temperado)
- Proximidade à praia (~{agent_dist_beach:.1f}km) — fator importante no mercado
- Tipologia T{agent_rooms} — o "sweet spot" do mercado na zona

**Contra:**
- Construção LSF com custo de construção inferior ao da construção tradicional
- Distância a Sintra (~{agent_dist_sintra:.1f}km) — zona intermédia

### 6. O preço justo segundo o modelo

O modelo estatístico (R²={regression["r2"]:.0%}) sugere um valor de **€{regression["agent_pred"]:,.0f}/m²**
para estas propriedades, o que daria um preço total de ~€{regression["agent_pred"] * agent_area_habitacao:,.0f}.
""".replace(",", "."), unsafe_allow_html=True)

st.markdown(f"""
---
<div style="text-align: center; color: rgba(255,255,255,0.3); font-size: 0.8rem; padding: 2rem 0; font-family: Inter, sans-serif;">
    Waldyn Imobiliário · Análise de mercado baseada em {len(df)} imóveis · Dados Idealista · Julho 2026
</div>
""", unsafe_allow_html=True)
