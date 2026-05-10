import streamlit as st
import asyncio
import pandas as pd
import numpy as np
from numba import njit
import time
from main import cities
from api import obtener_climas, obtener_todos_vuelos

st.set_page_config(layout="wide")
st.title("Dashboard de Vuelos y Clima")

st_autorefresh = True
if "last_update" not in st.session_state:
    st.session_state.last_update = time.time() - 31


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


if time.time() - st.session_state.last_update > 30:
    with st.spinner("Actualizando datos..."):
        weather_data, flight_data = asyncio.run(fetch_data())
        st.session_state.weather = weather_data
        st.session_state.flights = flight_data
        st.session_state.last_update = time.time()
else:
    weather_data = st.session_state.weather
    flight_data = st.session_state.flights

st.write(f"Última actualización: {time.ctime(st.session_state.last_update)}")

if weather_data and flight_data:
    df_weather = pd.DataFrame([w for w in weather_data if "error" not in w])

    flight_records = []
    for f in flight_data:
        if "error" not in f:
            for r in f.get("rutas", []):
                flight_records.append(
                    {
                        "ciudad": f["ciudad"],
                        "iata": f["iata"],
                        "origen": r.get("origen"),
                        "destino": r.get("destino"),
                        "retraso": r.get("retraso", 0),
                    }
                )
    df_flights = pd.DataFrame(flight_records)

    if not df_flights.empty and not df_weather.empty:
        df_merged = df_flights.merge(df_weather, on="ciudad", how="left")

        # relation between climate and delays
        st.subheader("Análisis de Retrasos y Clima")
        delays_arr = df_merged["retraso"].to_numpy(dtype=np.float64)
        # rain indicator applies to 'Rain'
        rain_ind = df_merged.apply(
            lambda row: (
                1 if ("Rain" in str(row["clima"])) or (row["visibilidad"] < 5000) else 0
            ),
            axis=1,
        ).to_numpy(dtype=np.float64)

        avg_all, avg_bad_weather = compute_delay_stats(delays_arr, rain_ind)

        col1, col2 = st.columns(2)
        col1.metric("Retraso promedio (General)", f"{avg_all:.2f} min")
        col2.metric("Retraso prom. (Mal clima/Baja vis.)", f"{avg_bad_weather:.2f} min")

        # airlines with highest amount of delays
        st.subheader("Aeropuertos con Mayor Cantidad de Retrasos")
        retrasos_por_aero = (
            df_merged.groupby("iata")["retraso"].mean().sort_values(ascending=False)
        )
        st.bar_chart(retrasos_por_aero)

        # aereal traffic and env conditions
        st.subheader("Tráfico Aéreo y Condiciones Ambientales")
        trafico_por_clima = df_merged.groupby("clima")["iata"].count()
        st.bar_chart(trafico_por_clima)

    time.sleep(30)
    st.rerun()
