import asyncio
import time

import numpy as np
import pandas as pd
import streamlit as st
from numba import njit

from api import obtener_climas, obtener_todos_vuelos
from data import cities

st.set_page_config(page_title="Dashboard de Vuelos y Clima", layout="wide")
st.title("Dashboard de Vuelos y Clima")


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
        with st.spinner("Actualizando datos..."):
            weather, flights = asyncio.run(fetch_data())
            st.session_state.weather = weather
            st.session_state.flights = flights
            st.session_state.last_update = time.time()


col_a, col_b = st.columns([1, 4])
with col_a:
    refresh = st.button("Actualizar datos")

load_data(force=refresh)

weather_data = st.session_state.get("weather", [])
flight_data = st.session_state.get("flights", [])
last_update = st.session_state.get("last_update")

if last_update:
    st.caption(f"Última actualización: {time.ctime(last_update)}")

# Mostrar errores de API para que el dashboard no se quede en blanco.
weather_errors = [w for w in weather_data if isinstance(w, dict) and "error" in w]
flight_errors = [f for f in flight_data if isinstance(f, dict) and "error" in f]

if weather_errors:
    st.warning(
        f"Clima: {len(weather_errors)} ciudades regresaron error. "
        "Abre el detalle abajo o revisa API_KEY / límite de OpenWeather."
    )
if flight_errors:
    st.warning(
        f"Vuelos: {len(flight_errors)} aeropuertos regresaron error. "
        "Abre el detalle abajo o revisa AIRLABS_API_KEY / plan (schedules puede estar restringido)."
    )

if weather_errors or flight_errors:
    with st.expander("Detalle de errores por ciudad", expanded=False):
        for w in weather_errors:
            st.text(f"[Clima] {w.get('ciudad', '?')}: {w.get('error', w)}")
        for f in flight_errors:
            st.text(f"[Vuelos] {f.get('ciudad', '?')}: {f.get('error', f)}")

valid_weather = [w for w in weather_data if isinstance(w, dict) and "error" not in w]
df_weather = pd.DataFrame(valid_weather)

flight_records = []
for f in flight_data:
    if isinstance(f, dict) and "error" not in f:
        for r in f.get("rutas", []):
            flight_records.append(
                {
                    "ciudad": f.get("ciudad"),
                    "iata": f.get("iata"),
                    "origen": r.get("origen"),
                    "destino": r.get("destino"),
                    "aerolinea": r.get("aerolinea"),
                    "retraso": r.get("retraso") or 0,
                }
            )

df_flights = pd.DataFrame(flight_records)

st.subheader("Datos obtenidos")
col1, col2, col3 = st.columns(3)
col1.metric("Ciudades con clima", len(df_weather))
col2.metric("Rutas/vuelos encontrados", len(df_flights))
col3.metric("Ciudades monitoreadas", len(cities))

with st.expander("Ver datos de clima"):
    if df_weather.empty:
        st.info("No hay datos válidos de clima para mostrar.")
    else:
        st.dataframe(df_weather, use_container_width=True)

with st.expander("Ver datos de vuelos"):
    if df_flights.empty:
        st.info("No hay datos válidos de vuelos para mostrar.")
    else:
        st.dataframe(df_flights, use_container_width=True)

if df_weather.empty or df_flights.empty:
    st.error("No se pueden generar gráficas porque falta clima o vuelos. Abre los desplegables de arriba para ver qué API no regresó datos.")
    st.stop()

# Unir datos
required_weather_cols = {"ciudad", "clima", "visibilidad"}
missing_cols = required_weather_cols - set(df_weather.columns)
if missing_cols:
    st.error(f"Faltan columnas de clima: {', '.join(missing_cols)}")
    st.stop()

df_merged = df_flights.merge(df_weather, on="ciudad", how="left")
df_merged["visibilidad"] = pd.to_numeric(df_merged["visibilidad"], errors="coerce").fillna(99999)
df_merged["retraso"] = pd.to_numeric(df_merged["retraso"], errors="coerce").fillna(0)

st.subheader("Análisis de Retrasos y Clima")
delays_arr = df_merged["retraso"].to_numpy(dtype=np.float64)
rain_ind = df_merged.apply(
    lambda row: 1 if ("Rain" in str(row.get("clima", ""))) or (row.get("visibilidad", 99999) < 5000) else 0,
    axis=1,
).to_numpy(dtype=np.float64)

avg_all, avg_bad_weather = compute_delay_stats(delays_arr, rain_ind)

col1, col2 = st.columns(2)
col1.metric("Retraso promedio general", f"{avg_all:.2f} min")
col2.metric("Retraso prom. mal clima/baja vis.", f"{avg_bad_weather:.2f} min")

st.subheader("Aeropuertos con Mayor Cantidad de Retrasos")
retrasos_por_aero = df_merged.groupby("iata")["retraso"].mean().sort_values(ascending=False)
st.bar_chart(retrasos_por_aero)

st.subheader("Tráfico Aéreo y Condiciones Ambientales")
trafico_por_clima = df_merged.groupby("clima")["iata"].count()
st.bar_chart(trafico_por_clima)

with st.expander("Ver datos combinados"):
    st.dataframe(df_merged, use_container_width=True)
