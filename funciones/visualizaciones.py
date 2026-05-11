import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLOR_MAP = {
    "Normal": "#059669",
    "Precaución": "#d97706",
    "Crítico": "#b91c1c",
}

_ACCENT_BARS = "#0f766e"
_ACCENT_MUTED = "#94a3b8"
_FONT = "'DM Sans', 'Segoe UI', system-ui, sans-serif"
_TEXT = "#1c1917"
_MUTED = "#57534e"
_PLOT_BG = "#fafaf9"


def _tema(fig, height=None):
    layout = dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=_PLOT_BG,
        font=dict(family=_FONT, size=13, color=_MUTED),
        title=dict(
            font=dict(size=15, color=_TEXT, family="'Instrument Sans', sans-serif"),
            x=0,
            xanchor="left",
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#e7e5e4",
            borderwidth=1,
        ),
        xaxis=dict(gridcolor="rgba(231,229,228,0.9)", linecolor="#d6d3d1", tickfont=dict(size=12)),
        yaxis=dict(gridcolor="rgba(231,229,228,0.9)", linecolor="#d6d3d1", tickfont=dict(size=12)),
        margin=dict(l=52, r=28, t=52, b=48),
    )
    if height is not None:
        layout["height"] = height
    fig.update_layout(**layout)
    return fig


def figura_vacia(titulo="Sin datos suficientes"):
    fig = go.Figure()
    fig.add_annotation(text=titulo, x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False)
    return _tema(fig, height=320)


def grafica_riesgo(df_pred):
    fig = px.bar(
        df_pred.sort_values("riesgo", ascending=True),
        x="riesgo",
        y="iata",
        orientation="h",
        color="nivel_operativo",
        color_discrete_map=COLOR_MAP,
        hover_data=["ciudad", "total_vuelos", "retraso_estimado_min", "motivo_riesgo"],
        title="Riesgo operativo por aeropuerto",
    )
    return _tema(fig, height=430)


def mapa_riesgo(df_pred):
    fig = px.scatter_mapbox(
        df_pred,
        lat="lat",
        lon="lon",
        size="riesgo",
        color="nivel_operativo",
        color_discrete_map=COLOR_MAP,
        hover_name="ciudad",
        hover_data={
            "iata": True,
            "riesgo": True,
            "nivel_operativo": True,
            "retraso_estimado_min": True,
            "motivo_riesgo": True,
            "lat": False,
            "lon": False,
        },
        zoom=4,
        height=620,
        title="Riesgo en mapa",
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        margin={"r": 0, "t": 48, "l": 0, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_FONT, size=13, color=_MUTED),
        title=dict(
            font=dict(size=15, color=_TEXT, family="'Instrument Sans', sans-serif"),
            x=0,
            xanchor="left",
        ),
    )
    return fig


def dona_niveles(df_pred):
    conteo = df_pred["nivel_operativo"].value_counts().reset_index()
    conteo.columns = ["nivel_operativo", "cantidad"]
    fig = px.pie(
        conteo,
        names="nivel_operativo",
        values="cantidad",
        hole=0.58,
        color="nivel_operativo",
        color_discrete_map=COLOR_MAP,
        title="Niveles operativos",
    )
    fig.update_traces(textposition="inside", textinfo="label+percent", textfont_size=12)
    return _tema(fig, height=380)


def grafica_retraso_estimado(df_pred):
    fig = px.bar(
        df_pred.sort_values("retraso_estimado_min", ascending=False),
        x="iata",
        y="retraso_estimado_min",
        color="nivel_operativo",
        color_discrete_map=COLOR_MAP,
        hover_data=["ciudad", "riesgo", "motivo_riesgo"],
        title="Retraso estimado (min)",
    )
    return _tema(fig, height=380)


def grafica_trafico_clima(df_merged):
    if df_merged.empty:
        return figura_vacia()
    data = df_merged.groupby("clima", as_index=False).agg(vuelos=("iata", "count"))
    fig = px.bar(
        data.sort_values("vuelos", ascending=False),
        x="clima",
        y="vuelos",
        title="Vuelos por tipo de clima",
        color_discrete_sequence=[_ACCENT_BARS],
    )
    fig.update_traces(marker_line_width=0, opacity=0.92)
    return _tema(fig, height=360)


def grafica_aerolineas(df_flights):
    if df_flights.empty or "aerolinea" not in df_flights.columns:
        return figura_vacia()
    data = (
        df_flights.groupby("aerolinea", as_index=False)
        .agg(vuelos=("vuelo", "count"), retraso_promedio=("retraso", "mean"))
        .sort_values("vuelos", ascending=False)
        .head(10)
    )
    fig = px.bar(
        data,
        x="aerolinea",
        y="vuelos",
        hover_data=["retraso_promedio"],
        title="Aerolíneas con más vuelos en el monitoreo",
        color_discrete_sequence=[_ACCENT_BARS],
    )
    fig.update_traces(marker_line_width=0, opacity=0.92)
    return _tema(fig, height=360)


def grafica_estados_vuelo(df_flights):
    if df_flights.empty or "estado" not in df_flights.columns:
        return figura_vacia()
    data = df_flights["estado"].fillna("sin dato").value_counts().reset_index()
    data.columns = ["estado", "vuelos"]
    fig = px.pie(data, names="estado", values="vuelos", hole=0.5, title="Estados de vuelo")
    return _tema(fig, height=360)


def grafica_rutas_frecuentes(df_flights):
    if df_flights.empty or not {"origen", "destino"}.issubset(df_flights.columns):
        return figura_vacia()
    df = df_flights.copy()
    df["ruta"] = df["origen"].fillna("?") + " → " + df["destino"].fillna("?")
    data = df.groupby("ruta", as_index=False).agg(vuelos=("vuelo", "count")).sort_values("vuelos", ascending=False).head(10)
    fig = px.bar(data.sort_values("vuelos"), x="vuelos", y="ruta", orientation="h", title="Rutas más frecuentes", color_discrete_sequence=[_ACCENT_BARS])
    return _tema(fig, height=380)


def grafica_calidad_aire_openaq(df_openaq):
    if df_openaq.empty:
        return figura_vacia("Sin datos OpenAQ. Revisa OPENAQ_API_KEY o estaciones cercanas.")
    data = df_openaq.copy()
    data["parametro"] = data["parametro"].astype(str).str.lower()
    data = data.sort_values("valor", ascending=False).head(50)
    fig = px.bar(
        data,
        x="ciudad",
        y="valor",
        color="parametro",
        hover_data=["iata", "location_name", "fecha_local", "sensor_id"],
        title="Últimas mediciones de calidad del aire (OpenAQ)",
    )
    fig.update_traces(marker_line_width=0, opacity=0.92)
    return _tema(fig, height=430)


def mapa_calidad_aire(df_openaq):
    if df_openaq.empty or not {"lat", "lon"}.issubset(df_openaq.columns):
        return figura_vacia("Sin coordenadas OpenAQ")
    data = df_openaq.dropna(subset=["lat", "lon", "valor"]).copy()
    if data.empty:
        return figura_vacia("Sin mediciones OpenAQ para mapa")
    fig = px.scatter_mapbox(
        data,
        lat="lat",
        lon="lon",
        size="valor",
        color="parametro",
        hover_name="ciudad",
        hover_data=["iata", "location_name", "valor", "unidad", "fecha_local"],
        zoom=4,
        height=480,
        title="Estaciones cercanas de OpenAQ",
    )
    fig.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 48, "l": 0, "b": 0})
    return fig


def grafica_thingspeak_series(df_thingspeak):
    if df_thingspeak.empty:
        return figura_vacia("Sin datos ThingSpeak")
    id_cols = {"channel_id", "channel_name", "created_at", "entry_id"}
    numeric_cols = [c for c in df_thingspeak.columns if c not in id_cols and pd.api.types.is_numeric_dtype(df_thingspeak[c])]
    if not numeric_cols:
        return figura_vacia("ThingSpeak no regresó campos numéricos")
    data = df_thingspeak[["created_at"] + numeric_cols].melt(id_vars="created_at", var_name="sensor", value_name="valor").dropna()
    fig = px.line(data, x="created_at", y="valor", color="sensor", markers=True, title="Historial del canal ThingSpeak")
    return _tema(fig, height=420)


def indicador_gpu(metricas):
    fig = go.Figure(go.Indicator(
        mode="number+delta",
        value=metricas.get("tiempo_ms", 0),
        number={"suffix": " ms", "font": {"size": 48}},
        delta={"reference": 1, "relative": False, "suffix": " ms"},
        title={"text": f"Backend: {metricas.get('backend', 'N/D')}"},
    ))
    return _tema(fig, height=250)
