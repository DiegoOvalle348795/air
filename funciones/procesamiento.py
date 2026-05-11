import re
import pandas as pd


# -----------------------------
# Limpieza base
# -----------------------------

def crear_df_clima(weather_data):
    valid_weather = [
        w for w in weather_data
        if isinstance(w, dict) and "error" not in w
    ]
    return pd.DataFrame(valid_weather)


def crear_df_vuelos(flight_data):
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
                        "vuelo": r.get("vuelo"),
                        "estado": r.get("estado"),
                        "hora_salida": r.get("hora_salida"),
                        "hora_llegada": r.get("hora_llegada"),
                        "retraso": r.get("retraso") or 0,
                        "retraso_salida": r.get("retraso_salida") or 0,
                        "retraso_llegada": r.get("retraso_llegada") or 0,
                        "duracion": r.get("duracion"),
                        "avion": r.get("avion"),
                    }
                )
    df = pd.DataFrame(flight_records)
    if not df.empty:
        for col in ["retraso", "retraso_salida", "retraso_llegada", "duracion"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def crear_df_openaq(openaq_data):
    """Convierte las mediciones de OpenAQ a tabla larga.

    Cada fila representa una medición de un sensor/estación cercana al aeropuerto:
    ciudad, iata, contaminante, valor, unidad, fecha y coordenadas.
    """
    registros = []
    for ciudad in openaq_data or []:
        if isinstance(ciudad, dict) and "error" not in ciudad:
            registros.extend(ciudad.get("mediciones", []))
    df = pd.DataFrame(registros)
    if not df.empty:
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df = df.dropna(subset=["valor"])
    return df


def crear_df_thingspeak(thingspeak_data):
    """Convierte el canal de ThingSpeak a tabla.

    ThingSpeak devuelve field1, field2, etc.; en api.py esos campos se renombran
    usando el nombre configurado en el canal. Aquí intentamos convertir todo lo
    que parezca numérico para poder graficarlo y usarlo en el score.
    """
    if not isinstance(thingspeak_data, dict) or thingspeak_data.get("error"):
        return pd.DataFrame()
    df = pd.DataFrame(thingspeak_data.get("registros", []))
    if df.empty:
        return df
    for col in df.columns:
        if col not in ["channel_id", "channel_name", "created_at", "entry_id"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


def unir_datos(df_weather, df_flights):
    if df_weather.empty or df_flights.empty:
        return pd.DataFrame()

    df_merged = df_flights.merge(df_weather, on=["ciudad", "iata"], how="left")

    numeric_cols = [
        "retraso", "retraso_salida", "retraso_llegada", "duracion",
        "temperatura", "sensacion_termica", "humedad", "presion", "visibilidad",
        "viento_velocidad", "viento_rafaga", "viento_direccion", "nubosidad", "lluvia_1h",
        "lat", "lon",
    ]
    for col in numeric_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce")

    df_merged["visibilidad"] = df_merged.get("visibilidad", 10000).fillna(10000)
    df_merged["viento_velocidad"] = df_merged.get("viento_velocidad", 0).fillna(0)
    df_merged["humedad"] = df_merged.get("humedad", 0).fillna(0)
    df_merged["nubosidad"] = df_merged.get("nubosidad", 0).fillna(0)
    df_merged["lluvia_1h"] = df_merged.get("lluvia_1h", 0).fillna(0)
    df_merged["retraso"] = df_merged.get("retraso", 0).fillna(0)
    return df_merged


# -----------------------------
# OpenAQ: de mediciones a variables usables
# -----------------------------

def _normalizar_parametro_aire(param):
    p = str(param).lower().strip()
    p = p.replace("µ", "u").replace("μ", "u")
    p = re.sub(r"[^a-z0-9]+", "", p)
    equivalencias = {
        "pm25": "pm25", "pm2_5": "pm25", "pm2p5": "pm25", "pm2": "pm25",
        "pm10": "pm10", "o3": "o3", "ozone": "o3", "ozono": "o3",
        "no2": "no2", "nitrogendioxide": "no2",
        "so2": "so2", "sulfurdioxide": "so2",
        "co": "co", "carbonmonoxide": "co",
    }
    return equivalencias.get(p, p)


def resumen_calidad_aire(df_openaq):
    if df_openaq.empty:
        return pd.DataFrame(columns=["iata", "aq_score", "aq_parametros", "aq_max_valor"])

    df = df_openaq.copy()
    df["parametro_norm"] = df["parametro"].apply(_normalizar_parametro_aire)

    pivot = (
        df.pivot_table(index="iata", columns="parametro_norm", values="valor", aggfunc="max")
        .reset_index()
    )

    for col in ["pm25", "pm10", "o3", "no2", "so2", "co"]:
        if col not in pivot.columns:
            pivot[col] = 0.0
        pivot[col] = pd.to_numeric(pivot[col], errors="coerce").fillna(0)

    # Puntaje 0-100 aproximado: no pretende ser AQI oficial, solo convierte
    # contaminantes a una variable comparable para el dashboard.
    pivot["aq_score"] = (
        (pivot["pm25"] / 35.0 * 35.0).clip(0, 35) +
        (pivot["pm10"] / 80.0 * 25.0).clip(0, 25) +
        (pivot["o3"] / 120.0 * 15.0).clip(0, 15) +
        (pivot["no2"] / 100.0 * 15.0).clip(0, 15) +
        (pivot["so2"] / 80.0 * 5.0).clip(0, 5) +
        (pivot["co"] / 10.0 * 5.0).clip(0, 5)
    ).fillna(0).round(1)

    resumen_parametros = (
        df.groupby("iata")
        .agg(
            aq_parametros=("parametro_norm", lambda s: ", ".join(sorted(set(map(str, s))))[:120]),
            aq_max_valor=("valor", "max"),
        )
        .reset_index()
    )
    return pivot.merge(resumen_parametros, on="iata", how="left")


# -----------------------------
# ThingSpeak: de canal IoT a variables usables
# -----------------------------

def _normalizar_nombre_columna(nombre):
    n = str(nombre).lower().strip()
    n = n.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    n = n.replace("µ", "u").replace("μ", "u")
    n = re.sub(r"[^a-z0-9]+", "", n)
    return n


def _detectar_columna(df, candidatos):
    """Busca una columna por palabras clave normalizadas."""
    mapa = {_normalizar_nombre_columna(col): col for col in df.columns}
    for esperado in candidatos:
        esperado_norm = _normalizar_nombre_columna(esperado)
        for norm, original in mapa.items():
            if esperado_norm in norm:
                return original
    return None


def resumen_sensores_thingspeak(df_thingspeak):
    """Extrae la lectura más reciente de ThingSpeak y calcula un iot_score.

    El canal puede tener nombres de campos distintos. Esta función intenta detectar:
    temperatura, humedad, presión, PM2.5, PM10, luz, viento y dirección del viento.

    El resultado se usa como variables ambientales adicionales. Si tu canal
    representa sensores de una ciudad/región, el score se puede sumar al riesgo.
    """
    columnas = [
        "sensor_temp", "sensor_humedad", "sensor_presion", "sensor_pm25", "sensor_pm10",
        "sensor_luz", "sensor_viento", "sensor_dir_viento", "iot_score", "iot_motivo", "iot_channel",
    ]
    if df_thingspeak.empty:
        return pd.DataFrame([{col: 0 for col in columnas}])

    df = df_thingspeak.copy()
    if "created_at" in df.columns:
        df = df.sort_values("created_at")
    latest = df.tail(1).iloc[0]

    col_temp = _detectar_columna(df, ["temperatura", "temperature", "temp", "field1"])
    col_hum = _detectar_columna(df, ["humedad", "humidity", "hum", "field2"])
    col_pres = _detectar_columna(df, ["presion", "pressure", "pres", "barometric"])
    col_pm25 = _detectar_columna(df, ["pm2.5", "pm25", "pm 2.5", "particulate2.5"])
    col_pm10 = _detectar_columna(df, ["pm10", "pm 10", "particulate10"])
    col_luz = _detectar_columna(df, ["luz", "light", "luminosidad", "lux"])
    col_viento = _detectar_columna(df, ["velocidadviento", "viento", "windspeed", "wind"])
    col_dir = _detectar_columna(df, ["direccionviento", "winddirection", "dirviento"])

    def val(col):
        if not col:
            return 0.0
        try:
            v = latest.get(col, 0)
            if pd.isna(v):
                return 0.0
            return float(v)
        except Exception:
            return 0.0

    temp = val(col_temp)
    hum = val(col_hum)
    pres = val(col_pres)
    pm25 = val(col_pm25)
    pm10 = val(col_pm10)
    luz = val(col_luz)
    viento = val(col_viento)
    dir_viento = val(col_dir)

    score = 0.0
    motivos = []

    if temp >= 38 or (temp > 0 and temp <= 3):
        score += 10
        motivos.append("temperatura extrema")
    elif temp >= 34 or (temp > 0 and temp <= 8):
        score += 5
        motivos.append("temperatura exigente")

    if hum >= 90:
        score += 8
        motivos.append("humedad muy alta")
    elif hum >= 80:
        score += 4
        motivos.append("humedad alta")

    if pres and (pres < 1000 or pres > 1025):
        score += 5
        motivos.append("presión fuera de rango")

    if viento >= 14:
        score += 14
        motivos.append("viento fuerte por sensor")
    elif viento >= 9:
        score += 8
        motivos.append("viento moderado por sensor")

    if pm25 >= 35:
        score += 12
        motivos.append("PM2.5 alto por sensor")
    elif pm25 >= 15:
        score += 6
        motivos.append("PM2.5 moderado por sensor")

    if pm10 >= 80:
        score += 8
        motivos.append("PM10 alto por sensor")
    elif pm10 >= 40:
        score += 4
        motivos.append("PM10 moderado por sensor")

    if not motivos:
        motivos.append("sensores en rango normal")

    return pd.DataFrame([{
        "sensor_temp": round(temp, 2),
        "sensor_humedad": round(hum, 2),
        "sensor_presion": round(pres, 2),
        "sensor_pm25": round(pm25, 2),
        "sensor_pm10": round(pm10, 2),
        "sensor_luz": round(luz, 2),
        "sensor_viento": round(viento, 2),
        "sensor_dir_viento": round(dir_viento, 2),
        "iot_score": round(min(score, 100), 1),
        "iot_motivo": ", ".join(motivos[:5]),
        "iot_channel": str(latest.get("channel_name", latest.get("channel_id", "ThingSpeak"))),
    }])


def resumen_por_aeropuerto(df_weather, df_flights, df_openaq=None, df_thingspeak=None):
    if df_weather.empty:
        return pd.DataFrame()

    if df_flights.empty:
        resumen_vuelos = pd.DataFrame(columns=["iata", "total_vuelos", "retraso_promedio", "retraso_maximo"])
    else:
        resumen_vuelos = (
            df_flights
            .groupby("iata", as_index=False)
            .agg(
                total_vuelos=("vuelo", "count"),
                retraso_promedio=("retraso", "mean"),
                retraso_maximo=("retraso", "max"),
            )
        )

    columnas_clima = [
        "ciudad", "iata", "lat", "lon", "clima", "descripcion", "temperatura", "humedad",
        "presion", "visibilidad", "viento_velocidad", "viento_rafaga", "nubosidad", "lluvia_1h",
    ]
    columnas_clima = [col for col in columnas_clima if col in df_weather.columns]
    resumen = df_weather[columnas_clima].merge(resumen_vuelos, on="iata", how="left")

    resumen["total_vuelos"] = resumen["total_vuelos"].fillna(0).astype(int)
    resumen["retraso_promedio"] = pd.to_numeric(resumen["retraso_promedio"], errors="coerce").fillna(0)
    resumen["retraso_maximo"] = pd.to_numeric(resumen["retraso_maximo"], errors="coerce").fillna(0)

    # 1) OpenAQ sí se cruza por aeropuerto/IATA, porque se consulta por coordenadas cercanas a cada aeropuerto.
    if df_openaq is not None and not df_openaq.empty:
        resumen_aq = resumen_calidad_aire(df_openaq)
        resumen = resumen.merge(resumen_aq, on="iata", how="left")

    for col in ["pm25", "pm10", "o3", "no2", "so2", "co", "aq_score", "aq_max_valor"]:
        if col not in resumen.columns:
            resumen[col] = 0.0
        resumen[col] = pd.to_numeric(resumen[col], errors="coerce").fillna(0)
    if "aq_parametros" not in resumen.columns:
        resumen["aq_parametros"] = ""
    resumen["aq_parametros"] = resumen["aq_parametros"].fillna("")

    # 2) ThingSpeak normalmente es un canal IoT global o propio. Si tienes un canal por ciudad,
    # se puede extender para hacer merge por ciudad; por ahora se toma la última lectura del canal
    # configurado y se aplica como contexto ambiental del monitoreo.
    resumen_iot = resumen_sensores_thingspeak(df_thingspeak if df_thingspeak is not None else pd.DataFrame())
    for col in resumen_iot.columns:
        resumen[col] = resumen_iot.iloc[0][col]

    for col in ["sensor_temp", "sensor_humedad", "sensor_presion", "sensor_pm25", "sensor_pm10", "sensor_luz", "sensor_viento", "sensor_dir_viento", "iot_score"]:
        resumen[col] = pd.to_numeric(resumen[col], errors="coerce").fillna(0)
    resumen["iot_motivo"] = resumen.get("iot_motivo", "").fillna("")
    resumen["iot_channel"] = resumen.get("iot_channel", "").fillna("")

    return resumen
