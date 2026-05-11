import pandas as pd


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
    if not isinstance(thingspeak_data, dict) or thingspeak_data.get("error"):
        return pd.DataFrame()
    df = pd.DataFrame(thingspeak_data.get("registros", []))
    if df.empty:
        return df
    for col in df.columns:
        if col not in ["channel_id", "channel_name", "created_at", "entry_id"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
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


def resumen_calidad_aire(df_openaq):
    if df_openaq.empty:
        return pd.DataFrame(columns=["iata", "aq_score", "aq_parametros", "aq_max_valor"])

    def normalizar_parametro(param):
        p = str(param).lower().replace(".", "").replace(" ", "")
        if p in ["pm25", "pm2_5", "pm2,5", "pm2-5"]:
            return "pm25"
        if p in ["pm10", "pm_10"]:
            return "pm10"
        if p in ["o3", "ozone"]:
            return "o3"
        if p in ["no2", "nitrogendioxide"]:
            return "no2"
        if p in ["so2", "sulfurdioxide"]:
            return "so2"
        if p in ["co", "carbonmonoxide"]:
            return "co"
        return str(param).lower()

    df = df_openaq.copy()
    df["parametro_norm"] = df["parametro"].apply(normalizar_parametro)

    pivot = (
        df.pivot_table(index="iata", columns="parametro_norm", values="valor", aggfunc="max")
        .reset_index()
    )

    for col in ["pm25", "pm10", "o3", "no2", "so2", "co"]:
        if col not in pivot.columns:
            pivot[col] = 0.0

    # Puntaje simple de calidad del aire para integrarlo al riesgo operacional.
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


def resumen_por_aeropuerto(df_weather, df_flights, df_openaq=None):
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
    return resumen
