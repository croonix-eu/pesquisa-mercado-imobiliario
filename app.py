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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .block-container { max-width: 1100px; padding-top: 2rem; }

    h1, h2, h3 { font-family: 'Inter', system-ui, sans-serif !important; }

    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border-left: 4px solid #1B5E8C;
        margin-bottom: 0.5rem;
    }
    .metric-card.agent {
        border-left-color: #C2703E;
        background: linear-gradient(135deg, #fef3ec 0%, #fde8d8 100%);
    }
    .metric-card.alert {
        border-left-color: #B83D3D;
        background: linear-gradient(135deg, #fef2f2 0%, #fde8e8 100%);
    }
    .metric-card .label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6c757d;
        margin-bottom: 0.25rem;
    }
    .metric-card .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        line-height: 1.1;
    }
    .metric-card .detail {
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 0.25rem;
    }

    .finding-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 1rem 0;
        font-size: 0.95rem;
        line-height: 1.6;
    }
    .finding-box.info {
        background: #e8f4f8;
        border-color: #1B5E8C;
    }
    .finding-box.danger {
        background: #fde8e8;
        border-color: #B83D3D;
    }

    .section-intro {
        font-size: 1.05rem;
        color: #495057;
        line-height: 1.7;
        margin-bottom: 1.5rem;
        max-width: 800px;
    }

    div[data-testid="stMetric"] {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.75rem;
        border: 1px solid #dee2e6;
    }
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

    # Partial dependence
    pd_data = {}
    top_features = sorted(importances, key=importances.get, reverse=True)[:4]
    for feat in top_features:
        feat_idx = features.index(feat)
        vals = np.linspace(X[:, feat_idx].min(), X[:, feat_idx].max(), 25)
        pd_vals = []
        for v in vals:
            X_temp = X.copy()
            X_temp[:, feat_idx] = v
            pd_vals.append(model.predict(X_temp).mean())
        pd_data[feat] = {"x": vals.tolist(), "y": pd_vals}

    return {
        "r2": r2,
        "n": len(model_df),
        "importances": importances,
        "predictions": model_df[["listing_id", "price_per_sqm", "predicted", "residual_pct", "is_agent"]],
        "agent_pred": agent_pred,
        "pd_data": pd_data,
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
    nearby = nearby[nearby["has_pool"] != True]  # noqa: E712

    return nearby.sort_values("price_eur")


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
agent_area_listed = 435.0  # what Idealista originally showed (overridden in data)
agent_area_bruta = agent_df["area_bruta_sqm"].iloc[0]  # now = 223.91 (habitação)
agent_area_util = agent_area_bruta
agent_psqm = agent_df["price_per_sqm"].iloc[0]  # now based on 223.91m²
agent_psqm_construcao = agent_price / agent_area_construcao
agent_psqm_util = agent_psqm  # same as psqm since area_bruta = habitação
agent_psqm_listed = agent_price / agent_area_listed  # €/m² with original 435m²
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
    "ocean": "#1B5E8C",
    "terra": "#C2703E",
    "pos": "#2D7D5F",
    "neg": "#B83D3D",
    "muted": "#8c8c8c",
    "light_bg": "#f0f2f6",
}


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════

st.markdown("#### 🏠 Waldyn Imobiliário")
st.markdown("# Estas casas são caras ou baratas?")
st.markdown(f"""
<p class="section-intro">
Analisámos <strong>{len(df)} imóveis</strong> à venda na zona de Sintra/Cascais para perceber se as
3 propriedades do agente Century 21 Nações estão bem posicionadas no mercado.
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
Três números que resumem a situação. O preço pedido, o que o modelo estatístico prevê,
e a posição relativa quando comparamos com imóveis verdadeiramente semelhantes.
</p>
""", unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(f"""
    <div class="metric-card agent">
        <div class="label">Preço pedido</div>
        <div class="value">{fmt_eur(agent_price)}</div>
        <div class="detail">3 moradias T{agent_rooms} · Century 21</div>
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
        <div class="label">Habitação</div>
        <div class="value">{agent_area_habitacao:.0f}m²</div>
        <div class="detail">Área habitável real</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("#### O que muda quando usamos a área real")

c4, c5, c6 = st.columns(3)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">€/m² no anúncio original (435m²)</div>
        <div class="value">{fmt_eur(agent_psqm_listed)}/m²</div>
        <div class="detail">Área fictícia — não existe na documentação</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">€/m² construção ({agent_area_construcao:.0f}m²)</div>
        <div class="value">{fmt_eur(agent_psqm_construcao)}/m²</div>
        <div class="detail">Área bruta de construção real</div>
    </div>
    """, unsafe_allow_html=True)

with c6:
    st.markdown(f"""
    <div class="metric-card agent">
        <div class="label">€/m² habitação ({agent_area_habitacao:.0f}m²)</div>
        <div class="value">{fmt_eur(agent_psqm)}/m²</div>
        <div class="detail">Usado em toda esta análise</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown(f"""
<div class="finding-box danger">
⚠️ <strong>O anúncio original dizia 435m² — mas esse número não existe.</strong>
A documentação real mostra: lote de {agent_area_lote:.0f}m², construção bruta de {agent_area_construcao:.0f}m²,
e habitação de {agent_area_habitacao:.0f}m². Os 435m² do Idealista não correspondem a nenhuma destas medidas.
<br><br>
<strong>Toda esta análise usa a área de habitação ({agent_area_habitacao:.0f}m²)</strong> como base de comparação,
por ser a medida mais honesta e comparável com os restantes imóveis do mercado.
O €/m² passa de €{agent_psqm_listed:,.0f} (anúncio) para <strong>€{agent_psqm:,.0f}/m²</strong> (habitação).
</div>
""".replace(",", "."), unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: The paradox — cheap or expensive?
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🔍 Barato ou caro? Depende de como se mede")
st.markdown("""
<p class="section-intro">
O mesmo imóvel pode parecer barato ou caro, dependendo da métrica usada.
Abaixo, cada barra mostra a posição do agente: se está acima de 50%, é mais caro que a maioria.
As barras <strong style="color:#2D7D5F">verdes</strong> são métricas onde parece barato;
as <strong style="color:#B83D3D">vermelhas</strong>, onde é caro.
</p>
""", unsafe_allow_html=True)

pct_data = [
    ("€/m² bruto — mercado total", pct_market, False),
    ("€/m² bruto — comparáveis 3km", pct_comps_psqm, False),
    ("Preço absoluto — comparáveis 3km", pct_comps_abs, True),
    ("Preço absoluto — T4 comparáveis", pct_comps_abs_t4, True),
    ("Preço por quarto", pct_per_room, True),
    ("Preço por casa de banho", pct_per_wc, True),
]

fig_pct = go.Figure()
for label, pct, is_expensive in reversed(pct_data):
    color = CHART_COLORS["neg"] if is_expensive else CHART_COLORS["pos"]
    fig_pct.add_trace(go.Bar(
        y=[label],
        x=[pct],
        orientation="h",
        marker_color=color,
        opacity=0.8,
        text=[f"P{pct:.0f}"],
        textposition="outside",
        textfont=dict(size=13, color=color),
        hovertemplate=f"<b>{label}</b><br>Percentil: {pct:.0f}<br>Mais caro que {pct:.0f}% dos comparáveis<extra></extra>",
    ))

fig_pct.add_vline(x=50, line_dash="dot", line_color="#999", line_width=1,
                  annotation_text="Mediana", annotation_position="top")

fig_pct.update_layout(
    height=320,
    showlegend=False,
    xaxis=dict(range=[0, 105], title="Percentil (P50 = metade do mercado)", showgrid=True, gridcolor="#eee"),
    yaxis=dict(automargin=True),
    margin=dict(l=10, r=40, t=20, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
)

st.plotly_chart(fig_pct, use_container_width=True)

st.markdown("""
<div class="finding-box info">
💡 <strong>Como ler este gráfico:</strong> Se a barra chega a P83, significa que este imóvel é
mais caro que 83% dos imóveis comparáveis. Abaixo de P50, é mais barato que a maioria.
O facto de as barras verdes (€/m²) e vermelhas (preço real) contarem histórias opostas
é o ponto central desta análise.
</div>
""", unsafe_allow_html=True)


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
    marker_color=CHART_COLORS["ocean"],
    text=[f"{v:.1f}%" for v in vals],
    textposition="outside",
    textfont=dict(size=12),
    hovertemplate="<b>%{y}</b><br>Importância: %{x:.1f}%<extra></extra>",
))

fig_imp.update_layout(
    height=420,
    showlegend=False,
    xaxis=dict(title="Importância no preço (%)", showgrid=True, gridcolor="#eee"),
    yaxis=dict(automargin=True),
    margin=dict(l=10, r=40, t=10, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
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
# SECTION 4: How each factor moves the price
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 📈 Como cada fator move o preço")
st.markdown("""
<p class="section-intro">
Cada gráfico mostra como o preço médio por m² muda quando um fator varia, mantendo
tudo o resto igual. A <strong style="color:#C2703E">linha laranja tracejada</strong> marca
a posição das propriedades do agente.
</p>
""", unsafe_allow_html=True)

agent_feat_vals = {
    "area_bruta_sqm": agent_area_habitacao,
    "dist_sintra_km": df[df["is_agent"]]["dist_sintra_km"].iloc[0],
    "dist_beach_km": df[df["is_agent"]]["dist_beach_km"].iloc[0],
    "num_rooms": agent_rooms,
}

pd_cols = st.columns(2)

for i, (feat, pd_d) in enumerate(regression["pd_data"].items()):
    col = pd_cols[i % 2]
    with col:
        agent_val = agent_feat_vals.get(feat, None)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pd_d["x"],
            y=pd_d["y"],
            mode="lines+markers",
            line=dict(color=CHART_COLORS["ocean"], width=2.5),
            marker=dict(size=5),
            name="Preço médio previsto",
            hovertemplate="Valor: %{x:.1f}<br>€/m²: %{y:,.0f}<extra></extra>",
        ))

        if agent_val is not None:
            fig.add_vline(
                x=agent_val, line_dash="dash", line_color=CHART_COLORS["terra"], line_width=2,
                annotation_text=f"Agente: {agent_val:.1f}",
                annotation_font_color=CHART_COLORS["terra"],
                annotation_font_size=11,
            )

        feat_label = FEAT_NAMES.get(feat, feat)
        fig.update_layout(
            title=dict(text=feat_label, font=dict(size=14)),
            height=280,
            showlegend=False,
            xaxis=dict(title=feat_label, showgrid=True, gridcolor="#f0f0f0"),
            yaxis=dict(title="€/m² previsto", showgrid=True, gridcolor="#f0f0f0"),
            margin=dict(l=10, r=10, t=40, b=40),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown(f"""
<div class="finding-box">
🏠 <strong>Posição do agente:</strong> Com {agent_area_habitacao:.0f}m² de área habitável, estas casas
estão no segmento médio-grande. A distância a Sintra ({agent_feat_vals.get("dist_sintra_km", 0):.1f}km)
coloca-as numa zona intermédia. A proximidade à praia (~{agent_feat_vals.get("dist_beach_km", 0):.1f}km)
é o principal fator a favor.
</div>
""", unsafe_allow_html=True)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Actual vs Predicted scatter
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🎯 Preço real vs. previsão do modelo")
st.markdown("""
<p class="section-intro">
Cada ponto é um imóvel. Se está <strong>acima</strong> da linha diagonal, o preço real é superior
ao que o modelo prevê (sobrevalorizado). Se está <strong>abaixo</strong>, o preço é inferior ao previsto
(subvalorizado). Os pontos <strong style="color:#C2703E">laranjas</strong> são as propriedades do agente.
</p>
""", unsafe_allow_html=True)

preds = regression["predictions"]

fig_scatter = go.Figure()

market = preds[~preds["is_agent"]]
fig_scatter.add_trace(go.Scatter(
    x=market["predicted"],
    y=market["price_per_sqm"],
    mode="markers",
    marker=dict(color=CHART_COLORS["ocean"], size=5, opacity=0.3),
    name="Mercado",
    hovertemplate="Previsão: €%{x:,.0f}/m²<br>Real: €%{y:,.0f}/m²<br>Diferença: %{customdata:.1f}%<extra></extra>",
    customdata=market["residual_pct"],
))

agents = preds[preds["is_agent"]]
fig_scatter.add_trace(go.Scatter(
    x=agents["predicted"],
    y=agents["price_per_sqm"],
    mode="markers",
    marker=dict(color=CHART_COLORS["terra"], size=14, line=dict(color="white", width=2)),
    name="Agente (Century 21)",
    hovertemplate="<b>AGENTE</b><br>Previsão: €%{x:,.0f}/m²<br>Real: €%{y:,.0f}/m²<br>Diferença: %{customdata:.1f}%<extra></extra>",
    customdata=agents["residual_pct"],
))

max_val = min(preds[["predicted", "price_per_sqm"]].max().max() * 1.05, 15000)
fig_scatter.add_trace(go.Scatter(
    x=[0, max_val], y=[0, max_val],
    mode="lines",
    line=dict(color="#ccc", width=1, dash="dash"),
    showlegend=False,
    hoverinfo="skip",
))

fig_scatter.update_layout(
    height=500,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.8)"),
    xaxis=dict(title="Previsão do modelo (€/m²)", showgrid=True, gridcolor="#f0f0f0", range=[0, max_val]),
    yaxis=dict(title="Preço real (€/m²)", showgrid=True, gridcolor="#f0f0f0", range=[0, max_val]),
    margin=dict(l=10, r=10, t=10, b=40),
    plot_bgcolor="white",
    paper_bgcolor="white",
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
tipologia T3 a T5, em bom estado, sem piscina. As linhas <strong style="color:#C2703E">destacadas</strong>
são as propriedades do agente. A tabela está ordenada por preço.
</p>
""", unsafe_allow_html=True)

display_comps = comps[["title", "price_eur", "price_per_sqm", "area_bruta_sqm",
                        "tipologia", "is_agent"]].copy()

agent_mask = display_comps["is_agent"].values

display_comps = display_comps.rename(columns={
    "title": "Imóvel", "price_eur": "Preço", "price_per_sqm": "€/m²",
    "area_bruta_sqm": "Área (m²)", "tipologia": "Tipologia",
})

display_comps["Preço"] = display_comps["Preço"].apply(fmt_eur)
display_comps["€/m²"] = display_comps["€/m²"].apply(lambda x: fmt_eur(x))
display_comps["Área (m²)"] = display_comps["Área (m²)"].apply(lambda x: f"{x:.0f}" if pd.notna(x) else "—")
display_comps = display_comps.drop(columns=["is_agent"])

def highlight_agent(row):
    idx = row.name
    pos = display_comps.index.get_loc(idx)
    if agent_mask[pos]:
        return ["background-color: #fde8d8; font-weight: bold"] * len(row)
    return [""] * len(row)

styled = display_comps.style.apply(highlight_agent, axis=1)
st.dataframe(styled, use_container_width=True, height=600)


st.divider()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Map
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("## 🗺️ Mapa de comparáveis")
st.markdown("""
<p class="section-intro">
Localização geográfica dos imóveis comparáveis. Os pontos
<strong style="color:#C2703E">laranjas grandes</strong> são as propriedades do agente.
</p>
""", unsafe_allow_html=True)

map_data = comps[["latitude", "longitude", "price_eur", "title", "is_agent"]].copy()
map_data["Tipo"] = map_data["is_agent"].apply(lambda x: "Agente (Century 21)" if x else "Mercado")
map_data["size"] = map_data["is_agent"].apply(lambda x: 15 if x else 5)

scatter_fn = getattr(px, "scatter_map", None) or getattr(px, "scatter_mapbox")
map_style_key = "map_style" if hasattr(px, "scatter_map") else "mapbox_style"

fig_map = scatter_fn(
    map_data,
    lat="latitude",
    lon="longitude",
    size="size",
    color="Tipo",
    color_discrete_map={"Agente (Century 21)": CHART_COLORS["terra"], "Mercado": CHART_COLORS["ocean"]},
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
na conversa com o cliente ou o agente imobiliário.
</p>
""", unsafe_allow_html=True)

st.markdown(f"""
### 1. O anúncio original diz 435m² — esse número não existe

A documentação real mostra: lote {agent_area_lote:.0f}m², construção {agent_area_construcao:.0f}m²,
habitação {agent_area_habitacao:.0f}m². Os 435m² do Idealista não correspondem a nenhuma medida.
**Toda esta análise usa a área de habitação ({agent_area_habitacao:.0f}m²)** — a medida mais honesta
e comparável com os restantes imóveis do mercado.

### 2. €/m² real: €{agent_psqm:,.0f}/m²

Usando a área de habitação, o preço por m² é **€{agent_psqm:,.0f}/m²**.
Com os 435m² do anúncio original, seria apenas €{agent_psqm_listed:,.0f}/m² — um número
artificialmente baixo que não reflete a realidade.

### 3. Comparando com imóveis semelhantes

Quando filtramos por imóveis verdadeiramente comparáveis (mesma zona, tipologia T3-T5,
bom estado, sem piscina), estas propriedades são **mais caras que {pct_comps_abs:.0f}% dos
comparáveis** em preço absoluto.

### 4. O que valoriza (e desvaloriza) estas casas

**A favor:**
- Proximidade à praia (~{agent_feat_vals.get("dist_beach_km", 0):.1f}km) — fator importante no mercado
- Tipologia T{agent_rooms} — o "sweet spot" do mercado na zona

**Contra:**
- Distância a Sintra (~{agent_feat_vals.get("dist_sintra_km", 0):.1f}km) — zona intermédia, sem o premium de centralidade

### 5. O preço justo segundo o modelo

O modelo estatístico (R²={regression["r2"]:.0%}) sugere um valor de **€{regression["agent_pred"]:,.0f}/m²**
para estas propriedades, o que daria um preço total de ~€{regression["agent_pred"] * agent_area_habitacao:,.0f}.
""".replace(",", "."), unsafe_allow_html=True)

st.markdown(f"""
---
<div style="text-align: center; color: #999; font-size: 0.8rem; padding: 2rem 0;">
    Waldyn Imobiliário · Análise de mercado baseada em {len(df)} imóveis · Dados Idealista · Julho 2026
</div>
""", unsafe_allow_html=True)
