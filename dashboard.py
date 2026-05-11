import asyncio
import time

import numpy as np
import pandas as pd
import streamlit as st
from numba import njit

from api import obtener_climas, obtener_todos_vuelos
from data import cities
from funciones.estilos import cargar_estilos, tarjeta_riesgo
from funciones.predicciones import generar_predicciones
from funciones.procesamiento import crear_df_clima, crear_df_vuelos, resumen_por_aeropuerto, unir_datos
from funciones.visualizaciones import (
    dona_niveles,
    grafica_aerolineas,
    grafica_retraso_estimado,
    grafica_riesgo,
    grafica_trafico_clima,
    mapa_riesgo,
)

st.set_page_config(page_title="Air Risk Monitor", layout="wide")
cargar_estilos()

st.markdown(
    """
    <div class="hero">
        <h1>Monitoreo de Aviones Cabron</h1>
        <span class="tagline">Operaciones · México</span>
        <p>Clima en vivo, tráfico programado y un índice de riesgo por reglas.</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@njit
def compute_delay_stats(delays, rain_indicators):
    n = len(delays)
    if n == 0:
        return 0.0, 0.0

    total_delay = 0.0
    rain_delay = 0.0
    rain_count = 0

    for i in range(n):
        total_delay += delays[i]
        if rain_indicators[i] > 0:
            rain_delay += delays[i]
            rain_count += 1

    avg_total = total_delay / n
    avg_rain = rain_delay / rain_count if rain_count > 0 else 0.0
    return avg_total, avg_rain


async def fetch_data():
    weather = await obtener_climas(cities)
    flights = await obtener_todos_vuelos(cities)
    return weather, flights


def load_data(force=False):
    if force or "weather" not in st.session_state or "flights" not in st.session_state:
        with st.spinner("Actualizando datos de OpenWeather y AirLabs..."):
            weather, flights = asyncio.run(fetch_data())
            st.session_state.weather = weather
            st.session_state.flights = flights
            st.session_state.last_update = time.time()


col_a, col_b = st.columns([1, 4])
with col_a:
    refresh = st.button("Actualizar datos", use_container_width=True)

load_data(force=refresh)

weather_data = st.session_state.get("weather", [])
flight_data = st.session_state.get("flights", [])
last_update = st.session_state.get("last_update")

if last_update:
    st.caption(f"Última actualización: {time.ctime(last_update)}")

weather_errors = [w for w in weather_data if isinstance(w, dict) and "error" in w]
flight_errors = [f for f in flight_data if isinstance(f, dict) and "error" in f]

if weather_errors:
    st.warning(f"Clima: {len(weather_errors)} ciudades regresaron error.")
if flight_errors:
    st.warning(f"Vuelos: {len(flight_errors)} aeropuertos regresaron error.")

if weather_errors or flight_errors:
    with st.expander("Detalle de errores por ciudad", expanded=False):
        for w in weather_errors:
            st.text(f"[Clima] {w.get('ciudad', '?')}: {w.get('error', w)}")
        for f in flight_errors:
            st.text(f"[Vuelos] {f.get('ciudad', '?')}: {f.get('error', f)}")

df_weather = crear_df_clima(weather_data)
df_flights = crear_df_vuelos(flight_data)
df_merged = unir_datos(df_weather, df_flights)
df_resumen = resumen_por_aeropuerto(df_weather, df_flights)
df_pred = generar_predicciones(df_resumen)

if df_weather.empty or df_flights.empty or df_pred.empty:
    st.error("No se pueden generar predicciones porque falta clima o vuelos. Revisa los desplegables de datos y errores.")
    with st.expander("Ver datos de clima"):
        st.dataframe(df_weather, use_container_width=True)
    with st.expander("Ver datos de vuelos"):
        st.dataframe(df_flights, use_container_width=True)
    st.stop()

# Métricas principales
vuelos_totales = len(df_flights)
aeropuertos_monitoreados = len(df_pred)
retraso_promedio = df_flights["retraso"].mean() if not df_flights.empty else 0
aeropuerto_critico = df_pred.iloc[0]
riesgo_promedio = df_pred["riesgo"].mean()

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Vuelos monitoreados", f"{vuelos_totales:,}")
m2.metric("Aeropuertos", aeropuertos_monitoreados)
m3.metric("Retraso promedio", f"{retraso_promedio:.1f} min")
m4.metric("Riesgo promedio", f"{riesgo_promedio:.0f}%")
m5.metric("Más crítico", f"{aeropuerto_critico['iata']} · {aeropuerto_critico['riesgo']}%")

# Estadística con Numba
if not df_merged.empty:
    delays_arr = df_merged["retraso"].to_numpy(dtype=np.float64)
    rain_ind = df_merged.apply(
        lambda row: 1
        if ("Rain" in str(row.get("clima", ""))) or (row.get("visibilidad", 99999) < 5000)
        else 0,
        axis=1,
    ).to_numpy(dtype=np.float64)
    avg_all, avg_bad_weather = compute_delay_stats(delays_arr, rain_ind)
else:
    avg_all, avg_bad_weather = 0.0, 0.0

tab1, tab2, tab3, tab4 = st.tabs([
    "Resumen ejecutivo",
    "Mapa de riesgo",
    "Predicciones",
    "Datos en vivo",
])

with tab1:
    st.subheader("Aeropuertos que requieren más atención")
    col_left, col_right = st.columns([1.1, 1])
    with col_left:
        for _, row in df_pred.head(5).iterrows():
            st.markdown(tarjeta_riesgo(row), unsafe_allow_html=True)
    with col_right:
        st.plotly_chart(dona_niveles(df_pred), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.metric("Retraso general", f"{avg_all:.2f} min")
        c2.metric("Retraso con mal clima", f"{avg_bad_weather:.2f} min")

    st.plotly_chart(grafica_riesgo(df_pred), use_container_width=True)

with tab2:
    st.subheader("Mapa interactivo de riesgo")
    st.plotly_chart(mapa_riesgo(df_pred), use_container_width=True)
    st.caption("El tamaño del punto representa el porcentaje de riesgo. El color representa el nivel operativo.")

with tab3:
    st.subheader("Predicciones operativas por reglas")
    st.info(
        "El riesgo y el retraso estimado salen de reglas fijas sobre clima, visibilidad, viento, carga de vuelos y retrasos observados."
    )

    tabla_pred = df_pred[[
        "semaforo", "ciudad", "iata", "riesgo", "nivel_operativo",
        "probabilidad_retraso", "retraso_estimado_min", "total_vuelos",
        "retraso_promedio", "clima", "visibilidad", "viento_velocidad", "motivo_riesgo",
    ]].copy()
    tabla_pred = tabla_pred.rename(columns={
        "semaforo": "Semáforo",
        "ciudad": "Ciudad",
        "iata": "IATA",
        "riesgo": "Riesgo %",
        "nivel_operativo": "Nivel operativo",
        "probabilidad_retraso": "Prob. retraso %",
        "retraso_estimado_min": "Retraso estimado min",
        "total_vuelos": "Vuelos",
        "retraso_promedio": "Retraso promedio",
        "clima": "Clima",
        "visibilidad": "Visibilidad",
        "viento_velocidad": "Viento m/s",
        "motivo_riesgo": "Motivo",
    })
    st.dataframe(tabla_pred, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafica_retraso_estimado(df_pred), use_container_width=True)
    with col2:
        st.plotly_chart(grafica_trafico_clima(df_merged), use_container_width=True)

with tab4:
    st.subheader("Datos en vivo")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Clima")
        st.dataframe(df_weather, use_container_width=True)
    with col2:
        st.markdown("### Vuelos")
        st.dataframe(df_flights, use_container_width=True)

    st.markdown("### Aerolíneas")
    st.plotly_chart(grafica_aerolineas(df_flights), use_container_width=True)

    with st.expander("Ver datos combinados"):
        st.dataframe(df_merged, use_container_width=True)
