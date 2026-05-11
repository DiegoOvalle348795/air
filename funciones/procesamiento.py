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


def resumen_por_aeropuerto(df_weather, df_flights):
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
    return resumen
