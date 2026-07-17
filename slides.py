"""
Apresentação — Análise de Mercado Imobiliário (Fontanelas/Sintra)
Versão slides do dashboard, navegação com prev/next.
"""

import streamlit as st

st.set_page_config(
    page_title="Análise Imobiliária — Apresentação",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Slide CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .block-container {
        max-width: 1000px;
        padding-top: 1rem;
        padding-bottom: 0;
    }
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
    #MainMenu { display: none; }

    h1, h2, h3, p, div, span {
        font-family: 'Inter', system-ui, sans-serif !important;
    }

    /* Slide frame */
    .slide {
        min-height: 520px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .slide-center {
        min-height: 520px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }

    /* Typography */
    .slide-eyebrow {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.14em;
        color: #1B5E8C;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
    }
    .slide-title {
        font-size: 2rem;
        font-weight: 800;
        color: #1a1a2e;
        line-height: 1.15;
        letter-spacing: -0.02em;
        margin-bottom: 1rem;
    }
    .slide-subtitle {
        font-size: 1.1rem;
        color: #495057;
        line-height: 1.6;
        max-width: 720px;
    }
    .slide-subtitle-center {
        font-size: 1.1rem;
        color: #495057;
        line-height: 1.6;
        max-width: 640px;
        margin: 0 auto;
    }

    /* Cards */
    .s-card {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1.2rem 1.4rem;
        border-left: 3px solid #1B5E8C;
    }
    .s-card.coral { border-left-color: #B83D3D; }
    .s-card.teal { border-left-color: #2D7D5F; }
    .s-card.amber { border-left-color: #C2703E; }
    .s-card .s-card-label {
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #6c757d;
        text-transform: uppercase;
        margin-bottom: 0.3rem;
    }
    .s-card .s-card-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #1a1a2e;
        line-height: 1.1;
    }
    .s-card .s-card-value.coral { color: #B83D3D; }
    .s-card .s-card-value.teal { color: #2D7D5F; }
    .s-card .s-card-detail {
        font-size: 0.8rem;
        color: #6c757d;
        margin-top: 0.2rem;
    }

    /* Percentile bars */
    .pct-row {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 6px;
    }
    .pct-label {
        font-size: 0.78rem;
        color: #495057;
        width: 260px;
        text-align: right;
        flex-shrink: 0;
    }
    .pct-track {
        flex: 1;
        height: 22px;
        background: #f0f2f6;
        border-radius: 3px;
        position: relative;
        overflow: hidden;
    }
    .pct-fill {
        position: absolute;
        top: 0; bottom: 0; left: 0;
        border-radius: 3px;
        opacity: 0.75;
    }
    .pct-mid {
        position: absolute;
        top: 0; bottom: 0;
        left: 50%;
        width: 1px;
        background: #adb5bd;
    }
    .pct-val {
        font-size: 0.8rem;
        font-weight: 700;
        width: 42px;
        flex-shrink: 0;
    }

    /* Highlight box */
    .s-highlight {
        background: #fff3cd;
        border: 1px solid #ffc107;
        border-radius: 8px;
        padding: 0.9rem 1.1rem;
        font-size: 0.9rem;
        line-height: 1.6;
        margin-top: 1rem;
    }
    .s-highlight.danger {
        background: #fde8e8;
        border-color: #B83D3D;
    }
    .s-highlight.info {
        background: #e8f4f8;
        border-color: #1B5E8C;
    }

    /* Nav */
    .slide-nav {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        padding: 1rem 0 0.5rem;
        border-top: 1px solid #e9ecef;
        margin-top: 1rem;
    }
    .slide-counter {
        font-size: 0.8rem;
        color: #6c757d;
        font-weight: 600;
        letter-spacing: 0.05em;
        font-variant-numeric: tabular-nums;
    }

    /* Conclusion bullets */
    .s-bullet {
        display: flex;
        gap: 10px;
        margin-bottom: 0.6rem;
    }
    .s-bullet-icon {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.65rem;
        font-weight: 700;
        color: white;
        margin-top: 2px;
    }
    .s-bullet-text {
        font-size: 0.9rem;
        color: #495057;
        line-height: 1.5;
    }

    /* Divider */
    .s-divider {
        height: 1px;
        background: #e9ecef;
        margin: 1.2rem 0;
    }

    /* Cover brand */
    .s-brand {
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.15em;
        color: #adb5bd;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Slides
# ---------------------------------------------------------------------------

def slide_cover():
    st.markdown("""
    <div class="slide-center">
        <div class="s-brand">WALDYN IMOBILIÁRIO</div>
        <h1 class="slide-title" style="font-size:2.6rem; margin-top:2rem;">
            Análise de Mercado:<br>Fontanelas, Sintra
        </h1>
        <div style="width:200px; height:1px; background:#dee2e6; margin:1.5rem auto;"></div>
        <p class="slide-subtitle-center">
            Estas 3 moradias T4 estão bem posicionadas no mercado?<br>
            Análise baseada em <strong>998 imóveis</strong> à venda na zona de Sintra/Cascais.
        </p>
        <div style="margin-top:2rem;">
            <span class="s-brand">CENTURY 21 NAÇÕES · JULHO 2026</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def slide_numbers():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">OS NÚMEROS-CHAVE</div>
        <div class="slide-title">3 moradias T4 em Fontanelas, a 800m da praia.</div>
        <p class="slide-subtitle">
            A área anunciada (435m²) não corresponde à realidade documental.
            A área de habitação real é <strong>224m²</strong> — é esta que usamos em toda a análise.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("""
        <div class="s-card coral">
            <div class="s-card-label">Preço pedido</div>
            <div class="s-card-value coral">€1.350.000</div>
            <div class="s-card-detail">Por moradia</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Lote</div>
            <div class="s-card-value">552m²</div>
            <div class="s-card-detail">Área total do terreno</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Construção</div>
            <div class="s-card-value">254m²</div>
            <div class="s-card-detail">Área bruta de construção</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="s-card coral">
            <div class="s-card-label">Habitação</div>
            <div class="s-card-value coral">224m²</div>
            <div class="s-card-detail">€6.029/m² habitável</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="s-divider"></div>', unsafe_allow_html=True)

    c5, c6, c7 = st.columns(3)
    with c5:
        st.markdown("""
        <div class="s-card amber">
            <div class="s-card-label">€/m² de habitação</div>
            <div class="s-card-value">€6.029</div>
            <div class="s-card-detail">Preço real por m²</div>
        </div>
        """, unsafe_allow_html=True)
    with c6:
        st.markdown("""
        <div class="s-card teal">
            <div class="s-card-label">Tipologia</div>
            <div class="s-card-value">T4</div>
            <div class="s-card-detail">4 quartos · 4 casas de banho</div>
        </div>
        """, unsafe_allow_html=True)
    with c7:
        st.markdown("""
        <div class="s-card teal">
            <div class="s-card-label">Praia</div>
            <div class="s-card-value">0.8km</div>
            <div class="s-card-detail">Fator a favor no mercado</div>
        </div>
        """, unsafe_allow_html=True)


def slide_position():
    bars = [
        ("€/m² (habitação) — mercado total", 72),
        ("€/m² (habitação) — comparáveis 3km", 89),
        ("Preço absoluto — comparáveis 3km", 77),
        ("Preço absoluto — T4 comparáveis", 67),
        ("Preço por quarto", 72),
        ("Preço por casa de banho", 67),
    ]

    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">POSIÇÃO NO MERCADO</div>
        <div class="slide-title">Mais caras que a maioria em todas as métricas.</div>
        <p class="slide-subtitle" style="margin-bottom:1.5rem;">
            Cada barra mostra o percentil face ao mercado. P50 = metade.
            Acima de P50 = mais caro que a maioria.
        </p>
    """, unsafe_allow_html=True)

    bars_html = ""
    for label, pct in bars:
        color = "#B83D3D" if pct >= 50 else "#2D7D5F"
        bars_html += f"""
        <div class="pct-row">
            <div class="pct-label">{label}</div>
            <div class="pct-track">
                <div class="pct-fill" style="width:{pct}%; background:{color};"></div>
                <div class="pct-mid"></div>
            </div>
            <div class="pct-val" style="color:{color};">P{pct}</div>
        </div>
        """

    st.markdown(bars_html, unsafe_allow_html=True)

    st.markdown("""
        <div style="margin-top:0.8rem; font-size:0.75rem; color:#6c757d;">
            57 imóveis comparáveis: 3km de raio, T3–T5, bom estado, sem piscina
        </div>
    </div>
    """, unsafe_allow_html=True)


def slide_condition():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">ESTADO DE CONSERVAÇÃO</div>
        <div class="slide-title">Classificadas como "bom estado" — mas descritas como construção nova.</div>
        <p class="slide-subtitle">
            No Idealista, estão na categoria "segunda mão / bom estado".
            Mas o texto do anúncio diz "moradia de construção nova".
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="s-card teal">
            <div class="s-card-label">Construção nova</div>
            <div class="s-card-value">€6.417/m²</div>
            <div class="s-card-detail">71 imóveis · mediana €2.365.000</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Bom estado</div>
            <div class="s-card-value">€4.500/m²</div>
            <div class="s-card-detail">834 imóveis · mediana €1.150.000</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label" style="color:#adb5bd;">Para recuperar</div>
            <div class="s-card-value" style="color:#6c757d;">€3.445/m²</div>
            <div class="s-card-detail">88 imóveis · mediana €797.500</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="s-highlight info">
        Com <strong>€6.029/m²</strong>, o preço está alinhado com o segmento de
        <strong>construção nova</strong> (€6.417/m²), não com "bom estado" (€4.500/m²).
        Se a classificação estivesse correta, o preço seria competitivo dentro do seu segmento.
    </div>
    """, unsafe_allow_html=True)


def slide_lsf():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">TIPO DE CONSTRUÇÃO</div>
        <div class="slide-title">LSF custa menos a construir — mas está a ser vendido ao preço do betão.</div>
        <p class="slide-subtitle">
            O Idealista não indica o método construtivo. Classificámos cada imóvel
            por análise de texto dos anúncios. As propriedades do agente são
            <strong>LSF confirmado</strong> pelo cliente.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="s-card amber">
            <div class="s-card-label">Provável LSF</div>
            <div class="s-card-value">€3.905/m²</div>
            <div class="s-card-detail">12 imóveis no mercado</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Indeterminado</div>
            <div class="s-card-value">€4.933/m²</div>
            <div class="s-card-detail">20 imóveis</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Tradicional</div>
            <div class="s-card-value">€4.536/m²</div>
            <div class="s-card-detail">966 imóveis</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="s-highlight">
        O custo de construção LSF é tipicamente <strong>15-25% inferior</strong>
        ao da construção tradicional (betão/alvenaria). O agente cobra <strong>€6.029/m²</strong>
        — acima da mediana LSF de mercado (<strong>€3.905/m²</strong>).
    </div>
    """, unsafe_allow_html=True)


def slide_nova():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">O ARGUMENTO DA CONSTRUÇÃO NOVA</div>
        <div class="slide-title">
            "Está abaixo da mediana de construção nova"
            — <span style="color:#B83D3D;">este argumento é enganador.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Construção nova (todas)</div>
            <div class="s-card-value">€6.396/m²</div>
            <div class="s-card-detail">78 imóveis — mistura LSF com betão</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label" style="color:#1B5E8C;">Nova — tradicional</div>
            <div class="s-card-value">€6.860/m²</div>
            <div class="s-card-detail">62 imóveis — betão, mais caros</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="s-card coral">
            <div class="s-card-label" style="color:#B83D3D;">Nova — LSF / indet.</div>
            <div class="s-card-value coral">€4.816/m²</div>
            <div class="s-card-detail">16 imóveis — comparação real</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="s-highlight danger">
        A mediana de construção nova (€6.396/m²) inclui <strong>62 casas de betão armado</strong>
        a €6.860/m² que puxam o valor para cima. Quando se compara apenas com o segmento LSF/indeterminado,
        o agente está <strong style="color:#B83D3D;">25% acima</strong> da mediana.
    </div>
    """, unsafe_allow_html=True)


def slide_model():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">MODELO PREDITIVO</div>
        <div class="slide-title">O modelo estatístico sugere que o preço está 25% acima do previsto.</div>
        <p class="slide-subtitle">
            Gradient Boosting sobre 998 imóveis · R² = 88% · Analisa área, localização,
            tipologia, estado e amenidades.
        </p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="s-card teal">
            <div class="s-card-label">Previsão do modelo</div>
            <div class="s-card-value teal" style="font-size:2rem;">€4.810/m²</div>
            <div class="s-card-detail">≈ €1.077.000 por moradia</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="s-card coral">
            <div class="s-card-label">Preço pedido</div>
            <div class="s-card-value coral" style="font-size:2rem;">€6.029/m²</div>
            <div class="s-card-detail">€1.350.000 — 25% acima do modelo</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="s-divider"></div>', unsafe_allow_html=True)

    c3, c4, c5 = st.columns(3)
    with c3:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Precisão</div>
            <div class="s-card-value">R² = 88%</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Imóveis analisados</div>
            <div class="s-card-value">998</div>
        </div>
        """, unsafe_allow_html=True)
    with c5:
        st.markdown("""
        <div class="s-card">
            <div class="s-card-label">Fator dominante</div>
            <div class="s-card-value">Área (77%)</div>
        </div>
        """, unsafe_allow_html=True)


def slide_conclusions():
    st.markdown("""
    <div class="slide">
        <div class="slide-eyebrow">CONCLUSÕES</div>
        <div class="slide-title">O que dizer ao cliente.</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("""
        <div class="s-card" style="margin-bottom:0.8rem;">
            <div class="s-card-label">01 — O preço por m²</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                Com 224m² de habitação e €1.350.000, o custo real é <strong>€6.029/m²</strong>
                — acima de P72 no mercado geral e P89 entre comparáveis próximos.
            </div>
        </div>
        <div class="s-card" style="margin-bottom:0.8rem;">
            <div class="s-card-label">02 — Construção LSF</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                Estas casas são LSF, com custo de construção 15-25% inferior ao betão.
                A mediana LSF no mercado é <strong>€3.905/m²</strong>.
            </div>
        </div>
        <div class="s-card">
            <div class="s-card-label">03 — O argumento da construção nova</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                A mediana geral mistura betão (€6.860/m²) com LSF (€4.816/m²).
                Isolando o LSF, o agente está <strong>25% acima</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("""
        <div class="s-card" style="margin-bottom:0.8rem;">
            <div class="s-card-label">04 — O modelo diz</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                Modelo com R²=88% prevê <strong>€4.810/m²</strong>.
                Valor justo sugerido: <strong>~€1.077.000</strong>.
            </div>
        </div>
        <div class="s-card teal" style="margin-bottom:0.8rem;">
            <div class="s-card-label">A favor</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                • Construção nova com acabamentos de qualidade<br>
                • 800m da praia — fator importante<br>
                • T4 — o sweet spot da zona
            </div>
        </div>
        <div class="s-card coral">
            <div class="s-card-label">Contra</div>
            <div class="s-card-detail" style="font-size:0.88rem; color:#495057; margin-top:0.4rem;">
                • LSF com custo inferior ao tradicional<br>
                • Zona intermédia (6.9km de Sintra)<br>
                • Preço 25% acima do modelo
            </div>
        </div>
        """, unsafe_allow_html=True)


def slide_close():
    st.markdown("""
    <div class="slide-center">
        <div class="s-brand">WALDYN IMOBILIÁRIO</div>
        <div style="width:80px; height:1px; background:#dee2e6; margin:2rem auto;"></div>
        <p class="slide-subtitle-center" style="font-size:0.95rem;">
            Análise baseada em 998 imóveis · Dados Idealista · Julho 2026
        </p>
        <div style="margin-top:1.5rem;">
            <span style="font-size:0.85rem; color:#6c757d;">
                miguel.cunha@waldyn.eu · waldyn.eu
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
SLIDES = [
    ("Cover", slide_cover),
    ("Os números-chave", slide_numbers),
    ("Posição no mercado", slide_position),
    ("Estado de conservação", slide_condition),
    ("LSF vs. Tradicional", slide_lsf),
    ("O argumento da construção nova", slide_nova),
    ("Modelo preditivo", slide_model),
    ("Conclusões", slide_conclusions),
    ("", slide_close),
]

if "slide" not in st.session_state:
    st.session_state.slide = 0

total = len(SLIDES)
idx = st.session_state.slide

# Render current slide
SLIDES[idx][1]()

# Nav bar
nav_cols = st.columns([1, 1, 2, 1, 1])

with nav_cols[1]:
    if st.button("← Anterior", disabled=(idx == 0), use_container_width=True):
        st.session_state.slide = idx - 1
        st.rerun()

with nav_cols[2]:
    st.markdown(
        f'<div class="slide-counter" style="text-align:center; padding-top:8px;">'
        f'{idx + 1} / {total}</div>',
        unsafe_allow_html=True,
    )

with nav_cols[3]:
    if st.button("Seguinte →", disabled=(idx == total - 1), use_container_width=True):
        st.session_state.slide = idx + 1
        st.rerun()
