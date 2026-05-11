import asyncio
import time

import numpy as np
import streamlit as st
from numba import njit

from api import obtener_climas, obtener_openaq_ciudades, obtener_thingspeak, obtener_todos_vuelos
from data import cities
from funciones.aceleracion_gpu import metricas_numericas_aceleradas
from funciones.estilos import cargar_estilos, tarjeta_riesgo
from funciones.predicciones import generar_predicciones
from funciones.procesamiento import (
    crear_df_clima,
    crear_df_openaq,
    crear_df_thingspeak,
    crear_df_vuelos,
    resumen_por_aeropuerto,
    resumen_sensores_thingspeak,
    unir_datos,
)
from funciones.visualizaciones import (
    dona_niveles,
    grafica_aerolineas,
    grafica_calidad_aire_openaq,
    grafica_estados_vuelo,
    grafica_retraso_estimado,
    grafica_riesgo,
    grafica_rutas_frecuentes,
    grafica_thingspeak_series,
    grafica_trafico_clima,
    indicador_gpu,
    mapa_calidad_aire,
    mapa_riesgo,
)

st.set_page_config(page_title="Aviones Cabrones", layout="wide")
cargar_estilos()

st.markdown(
    """
    <div class="hero">
        <h1>Monitoreo de Aviones Cabron</h1>
        <span class="tagline">Operaciones aéreas · clima · sensores · calidad del aire</span>
        <p>Monitoreo de vuelos, clima, sensores IoT y calidad del aire con cálculo de riesgo por reglas.</p>
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
    weather_task = obtener_climas(cities)
    flights_task = obtener_todos_vuelos(cities)
    openaq_task = obtener_openaq_ciudades(cities)
    thingspeak_task = obtener_thingspeak()
    weather, flights, openaq, thingspeak = await asyncio.gather(
        weather_task,
        flights_task,
        openaq_task,
        thingspeak_task,
    )
    return weather, flights, openaq, thingspeak


def load_data(force=False):
    if force or "weather" not in st.session_state or "flights" not in st.session_state:
        with st.spinner("Actualizando APIs: OpenWeather, AirLabs, OpenAQ y ThingSpeak..."):
            weather, flights, openaq, thingspeak = asyncio.run(fetch_data())
            st.session_state.weather = weather
            st.session_state.flights = flights
            st.session_state.openaq = openaq
            st.session_state.thingspeak = thingspeak
            st.session_state.last_update = time.time()


col_a, col_b = st.columns([1, 4])
with col_a:
    refresh = st.button("Actualizar datos", use_container_width=True)

load_data(force=refresh)

weather_data = st.session_state.get("weather", [])
flight_data = st.session_state.get("flights", [])
openaq_data = st.session_state.get("openaq", [])
thingspeak_data = st.session_state.get("thingspeak", {})
last_update = st.session_state.get("last_update")

if last_update:
    st.caption(f"Última actualización: {time.ctime(last_update)}")

weather_errors = [w for w in weather_data if isinstance(w, dict) and "error" in w]
flight_errors = [f for f in flight_data if isinstance(f, dict) and "error" in f]
openaq_errors = [a for a in openaq_data if isinstance(a, dict) and "error" in a]
thingspeak_error = thingspeak_data.get("error") if isinstance(thingspeak_data, dict) else None

if weather_errors:
    st.warning(f"OpenWeather: {len(weather_errors)} ciudades regresaron error.")
if flight_errors:
    st.warning(f"AirLabs: {len(flight_errors)} aeropuertos regresaron error.")
if openaq_errors:
    st.warning(f"OpenAQ: {len(openaq_errors)} ciudades sin medición o con error. Revisa OPENAQ_API_KEY / estaciones cercanas.")
if thingspeak_error:
    st.warning(f"ThingSpeak: {thingspeak_error}")

if weather_errors or flight_errors or openaq_errors or thingspeak_error:
    with st.expander("Detalle de errores por fuente", expanded=False):
        for w in weather_errors:
            st.text(f"[OpenWeather] {w.get('ciudad', '?')}: {w.get('error', w)}")
        for f in flight_errors:
            st.text(f"[AirLabs] {f.get('ciudad', '?')}: {f.get('error', f)}")
        for a in openaq_errors:
            st.text(f"[OpenAQ] {a.get('ciudad', '?')}: {a.get('error', a)}")
        if thingspeak_error:
            st.text(f"[ThingSpeak] {thingspeak_error}")

# Limpieza y cruce de datos

df_weather = crear_df_clima(weather_data)
df_flights = crear_df_vuelos(flight_data)
df_openaq = crear_df_openaq(openaq_data)
df_thingspeak = crear_df_thingspeak(thingspeak_data)
df_merged = unir_datos(df_weather, df_flights)
df_resumen = resumen_por_aeropuerto(df_weather, df_flights, df_openaq, df_thingspeak)
df_sensor_iot = resumen_sensores_thingspeak(df_thingspeak)
df_pred = generar_predicciones(df_resumen)

if df_weather.empty or df_flights.empty or df_pred.empty:
    st.error("No se pueden generar predicciones porque falta clima o vuelos. Revisa los desplegables de datos y errores.")
    with st.expander("Ver datos de clima"):
        st.dataframe(df_weather, use_container_width=True)
    with st.expander("Ver datos de vuelos"):
        st.dataframe(df_flights, use_container_width=True)
    with st.expander("Ver datos OpenAQ"):
        st.dataframe(df_openaq, use_container_width=True)
    with st.expander("Ver datos ThingSpeak"):
        st.dataframe(df_thingspeak, use_container_width=True)
    st.stop()

# Métricas principales
vuelos_totales = len(df_flights)
aeropuertos_monitoreados = len(df_pred)
retraso_promedio = df_flights["retraso"].mean() if not df_flights.empty else 0
aeropuerto_critico = df_pred.iloc[0]
riesgo_promedio = df_pred["riesgo"].mean()
mediciones_aq = len(df_openaq)
lecturas_iot = len(df_thingspeak)
iot_score_actual = float(df_sensor_iot["iot_score"].iloc[0]) if not df_sensor_iot.empty and "iot_score" in df_sensor_iot else 0
aq_score_promedio = df_pred["aq_score"].mean() if "aq_score" in df_pred.columns else 0

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Vuelos monitoreados", f"{vuelos_totales:,}")
m2.metric("Aeropuertos", aeropuertos_monitoreados)
m3.metric("Retraso promedio", f"{retraso_promedio:.1f} min")
m4.metric("Riesgo promedio", f"{riesgo_promedio:.0f}%")
m5.metric("OpenAQ score prom.", f"{aq_score_promedio:.1f}")
m6.metric("ThingSpeak score", f"{iot_score_actual:.1f}")

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

metricas_gpu = metricas_numericas_aceleradas(df_pred, df_flights)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Resumen ejecutivo",
    "Mapa de riesgo",
    "Predicciones",
    "Sensores y calidad del aire",
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
        "el riesgo y el retraso estimado salen de reglas fijas sobre clima, visibilidad, viento, carga de vuelos, retrasos observados y calidad del aire."
    )

    columnas_pred = [
        "semaforo", "ciudad", "iata", "riesgo", "nivel_operativo",
        "probabilidad_retraso", "retraso_estimado_min", "total_vuelos",
        "retraso_promedio", "clima", "visibilidad", "viento_velocidad",
        "pm25", "pm10", "aq_score", "sensor_temp", "sensor_humedad", "sensor_presion",
        "sensor_pm25", "sensor_pm10", "sensor_viento", "iot_score", "motivo_riesgo",
    ]
    columnas_pred = [col for col in columnas_pred if col in df_pred.columns]
    tabla_pred = df_pred[columnas_pred].copy()
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
        "pm25": "PM2.5",
        "pm10": "PM10",
        "aq_score": "Score OpenAQ",
        "sensor_temp": "Sensor temp",
        "sensor_humedad": "Sensor humedad",
        "sensor_presion": "Sensor presión",
        "sensor_pm25": "Sensor PM2.5",
        "sensor_pm10": "Sensor PM10",
        "sensor_viento": "Sensor viento",
        "iot_score": "Score ThingSpeak",
        "motivo_riesgo": "Motivo",
    })
    st.dataframe(tabla_pred, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(grafica_retraso_estimado(df_pred), use_container_width=True)
    with col2:
        st.plotly_chart(grafica_trafico_clima(df_merged), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(grafica_estados_vuelo(df_flights), use_container_width=True)
    with col4:
        st.plotly_chart(grafica_rutas_frecuentes(df_flights), use_container_width=True)

with tab4:
    st.subheader("Sensores IoT, calidad del aire")

    st.info(
        "meti lo del cuda aqui porque no quise hacer otra pestaña, de todos modos no funciona en mi MACBOOK PRO M5 de 40,000 pesos mexicanos"
    )

    st.markdown("### OpenAQ · estaciones cercanas a aeropuertos")
    st.caption(
        "por cada aeropuerto se busca una estación cercana con lat/lon; después se extraen contaminantes "
        "como PM2.5, PM10, O3, NO2, SO2 o CO. Con esos valores se calcula `aq_score`, que se suma al riesgo."
    )
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.plotly_chart(grafica_calidad_aire_openaq(df_openaq), use_container_width=True)
    with c2:
        st.plotly_chart(mapa_calidad_aire(df_openaq), use_container_width=True)

    columnas_aq = [c for c in ["ciudad", "iata", "parametro", "valor", "unidad", "location_name", "fecha_local"] if c in df_openaq.columns]
    if columnas_aq:
        with st.expander("Ver mediciones OpenAQ usadas en el score"):
            st.dataframe(df_openaq[columnas_aq].sort_values(["ciudad", "parametro"]), use_container_width=True, hide_index=True)

    st.markdown("### ThingSpeak · sensores ambientales del canal")
    st.caption(
        "se toma la lectura más reciente del canal y se detectan campos como temperatura, humedad, presión, "
        "PM2.5, PM10, luz o viento. Con eso se calcula `iot_score`, que también entra al riesgo."
    )

    sensor_row = df_sensor_iot.iloc[0].to_dict() if not df_sensor_iot.empty else {}
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("IoT score", f"{sensor_row.get('iot_score', 0):.1f}")
    s2.metric("Temp sensor", f"{sensor_row.get('sensor_temp', 0):.1f}")
    s3.metric("Humedad", f"{sensor_row.get('sensor_humedad', 0):.1f}")
    s4.metric("Presión", f"{sensor_row.get('sensor_presion', 0):.1f}")
    s5.metric("PM2.5", f"{sensor_row.get('sensor_pm25', 0):.1f}")
    s6.metric("Viento", f"{sensor_row.get('sensor_viento', 0):.1f}")
    st.caption(f"Motivo ThingSpeak: {sensor_row.get('iot_motivo', 'sin datos')} · Canal: {sensor_row.get('iot_channel', 'N/D')}")
    st.plotly_chart(grafica_thingspeak_series(df_thingspeak), use_container_width=True)

    with st.expander("Ver tabla ThingSpeak y resumen usado"):
        st.markdown("**Resumen que entra al score:**")
        st.dataframe(df_sensor_iot, use_container_width=True, hide_index=True)
        st.markdown("**Lecturas del canal:**")
        st.dataframe(df_thingspeak, use_container_width=True, hide_index=True)

    st.markdown("### CUDA / CuPy")
    st.caption("Si CuPy y una GPU NVIDIA CUDA están disponibles, estas métricas se calculan en GPU; si no, el sistema usa NumPy como respaldo para no romper el dashboard.")
    g1, g2, g3, g4 = st.columns(4)
    g1.metric("Backend", metricas_gpu.get("backend", "N/D"))
    g2.metric("Riesgo promedio", f"{metricas_gpu.get('riesgo_promedio', 0):.2f}%")
    g3.metric("Retraso prom.", f"{metricas_gpu.get('retraso_promedio', 0):.2f} min")
    g4.metric("Tiempo cálculo", f"{metricas_gpu.get('tiempo_ms', 0):.4f} ms")
    st.plotly_chart(indicador_gpu(metricas_gpu), use_container_width=True)
    st.code(metricas_gpu.get("mensaje", "Sin mensaje de GPU"), language="text")

with tab5:
    st.subheader("Datos en vivo")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### OpenWeather")
        st.dataframe(df_weather, use_container_width=True)
    with col2:
        st.markdown("### AirLabs")
        st.dataframe(df_flights, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("### OpenAQ")
        st.dataframe(df_openaq, use_container_width=True)
    with col4:
        st.markdown("### ThingSpeak")
        st.dataframe(df_thingspeak, use_container_width=True)

    st.markdown("### Aerolíneas")
    st.plotly_chart(grafica_aerolineas(df_flights), use_container_width=True)

    with st.expander("Ver datos combinados"):
        st.dataframe(df_merged, use_container_width=True)
