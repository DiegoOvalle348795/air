import streamlit as st


def cargar_estilos():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..700&family=Instrument+Sans:wght@500;600;700&display=swap');

            :root {
                --bg: #f4f1eb;
                --bg-elevated: #ffffff;
                --text: #1c1917;
                --muted: #57534e;
                --line: #e7e5e4;
                --accent: #0f766e;
                --accent-soft: rgba(15, 118, 110, 0.12);
                --shadow: 0 1px 2px rgba(28, 25, 23, 0.04), 0 8px 24px rgba(28, 25, 23, 0.06);
                --radius: 14px;
            }

            .stApp {
                background: var(--bg);
                color: var(--text);
            }

            [data-testid="stHeader"] {
                background: rgba(247, 245, 242, 0.92);
                backdrop-filter: blur(8px);
                border-bottom: 1px solid var(--line);
            }

            .block-container {
                padding-top: 1.75rem;
                padding-bottom: 3rem;
                max-width: 1180px;
            }

            /* Tipografía global */
            .stApp, .stMarkdown, [data-testid="stMetricLabel"] p {
                font-family: "DM Sans", "Segoe UI", system-ui, sans-serif;
            }

            /* Botones */
            .stButton > button {
                font-family: "Instrument Sans", "DM Sans", sans-serif;
                font-weight: 600;
                letter-spacing: 0.01em;
                border-radius: 10px !important;
                border: 1px solid var(--line) !important;
                background: var(--bg-elevated) !important;
                color: var(--text) !important;
                box-shadow: var(--shadow);
                transition: border-color 0.15s ease, box-shadow 0.15s ease;
            }
            .stButton > button:hover {
                border-color: var(--accent) !important;
                box-shadow: 0 2px 8px rgba(15, 118, 110, 0.12);
            }

            /* Métricas */
            div[data-testid="stMetric"] {
                background: var(--bg-elevated);
                border: 1px solid var(--line);
                border-radius: var(--radius);
                padding: 1rem 1.1rem;
                box-shadow: var(--shadow);
            }
            div[data-testid="stMetricLabel"] p {
                color: var(--muted) !important;
                font-size: 0.8125rem;
                font-weight: 500;
            }
            div[data-testid="stMetricValue"] {
                color: var(--text) !important;
                font-family: "Instrument Sans", sans-serif;
                font-weight: 700;
                letter-spacing: -0.02em;
            }

            /* Pestañas */
            .stTabs [data-baseweb="tab-list"] {
                gap: 4px;
                background: transparent;
                border-bottom: 1px solid var(--line);
                padding-bottom: 0;
            }
            .stTabs [data-baseweb="tab"] {
                font-family: "Instrument Sans", sans-serif;
                font-weight: 600;
                font-size: 0.9rem;
                color: var(--muted);
                border-radius: 10px 10px 0 0;
                padding: 0.65rem 1rem;
            }
            .stTabs [aria-selected="true"] {
                color: var(--accent) !important;
                background: var(--bg-elevated);
                border: 1px solid var(--line);
                border-bottom-color: var(--bg-elevated) !important;
                margin-bottom: -1px;
            }

            /* Info / warning */
            div[data-testid="stAlert"] {
                border-radius: var(--radius);
                border: 1px solid var(--line);
            }

            /* Dataframes */
            [data-testid="stDataFrame"] {
                border: 1px solid var(--line);
                border-radius: var(--radius);
                overflow: hidden;
            }

            /* Hero */
            .hero {
                position: relative;
                overflow: hidden;
                background: linear-gradient(135deg, #ffffff 0%, #f0fdf9 42%, #ecfdf5 100%);
                border: 1px solid var(--line);
                border-radius: 18px;
                padding: 1.75rem 1.85rem;
                margin-bottom: 1.5rem;
                box-shadow: var(--shadow);
            }
            .hero::after {
                content: "";
                position: absolute;
                top: -40%;
                right: -8%;
                width: 42%;
                height: 180%;
                background: radial-gradient(circle, var(--accent-soft) 0%, transparent 70%);
                pointer-events: none;
            }
            .hero h1 {
                position: relative;
                margin: 0;
                font-family: "Instrument Sans", sans-serif;
                font-weight: 700;
                font-size: clamp(1.65rem, 3vw, 2.1rem);
                letter-spacing: -0.03em;
                color: var(--text);
            }
            .hero .tagline {
                position: relative;
                display: inline-block;
                margin-top: 0.5rem;
                font-size: 0.78rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.14em;
                color: var(--accent);
            }
            .hero p {
                position: relative;
                margin: 0.65rem 0 0 0;
                max-width: 52ch;
                color: var(--muted);
                font-size: 1rem;
                line-height: 1.55;
            }

            /* Tarjetas de riesgo */
            .risk-card {
                position: relative;
                background: var(--bg-elevated);
                border: 1px solid var(--line);
                border-radius: var(--radius);
                padding: 1rem 1.1rem;
                margin-bottom: 10px;
                box-shadow: var(--shadow);
            }
            .risk-card h3 {
                margin: 0;
                font-family: "Instrument Sans", sans-serif;
                font-weight: 600;
                font-size: 1rem;
                letter-spacing: -0.01em;
                color: var(--text);
            }
            .risk-card p {
                margin: 0.4rem 0 0 0;
                font-size: 0.875rem;
                line-height: 1.45;
                color: var(--muted);
            }
            .risk-card .meta {
                margin-top: 0.5rem;
                font-size: 0.8rem;
                color: var(--muted);
            }
            .normal { border-left: 5px solid #059669; }
            .precaucion { border-left: 5px solid #d97706; }
            .critico { border-left: 5px solid #b91c1c; }

            /* Subtítulos de sección (Streamlit) */
            h2, h3 {
                font-family: "Instrument Sans", sans-serif !important;
                font-weight: 600 !important;
                letter-spacing: -0.02em !important;
                color: var(--text) !important;
            }
            h2 {
                font-size: 1.2rem !important;
                margin-top: 0.25rem !important;
                padding-bottom: 0.35rem;
                border-bottom: 2px solid var(--accent-soft);
            }

            /* Caption */
            .stCaption, [data-testid="stCaptionContainer"] {
                color: var(--muted) !important;
            }

            /* Expander */
            details summary {
                font-weight: 600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def tarjeta_riesgo(row):
    nivel = str(row.get("nivel_operativo", "Normal"))
    clase = {
        "Normal": "normal",
        "Precaución": "precaucion",
        "Crítico": "critico",
    }.get(nivel, "normal")
    return f"""
    <div class="risk-card {clase}">
        <h3>{row.get('semaforo', '')} {row.get('ciudad', '')} · {row.get('iata', '')}</h3>
        <p class="meta">{nivel} · Riesgo {row.get('riesgo', 0)}% · Retraso estimado {row.get('retraso_estimado_min', 0)} min · {row.get('total_vuelos', 0)} vuelos</p>
        <p>{row.get('motivo_riesgo', 'Condiciones dentro de lo esperado.')}</p>
    </div>
    """
