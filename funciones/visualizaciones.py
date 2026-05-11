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
        return go.Figure()
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
        return go.Figure()
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
