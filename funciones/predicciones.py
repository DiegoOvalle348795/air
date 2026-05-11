import pandas as pd


def _num(row, col, default=0):
    valor = row.get(col, default)
    try:
        if pd.isna(valor):
            return default
        return float(valor)
    except (TypeError, ValueError):
        return default


def calcular_riesgo(row):
    """
    Calcula un índice de riesgo operacional de 0 a 100.

    No es IA ni machine learning. Es una regla de puntaje:
    entre más factores negativos existan, más puntos suma el aeropuerto.
    Ahora también puede sumar riesgo por calidad del aire desde OpenAQ.
    """
    riesgo = 0
    motivos = []

    clima = str(row.get("clima", "")).lower()
    descripcion = str(row.get("descripcion", "")).lower()
    visibilidad = _num(row, "visibilidad", 10000)
    viento = _num(row, "viento_velocidad", 0)
    rafaga = _num(row, "viento_rafaga", 0)
    humedad = _num(row, "humedad", 0)
    nubosidad = _num(row, "nubosidad", 0)
    lluvia = _num(row, "lluvia_1h", 0)
    total_vuelos = _num(row, "total_vuelos", 0)
    retraso_promedio = _num(row, "retraso_promedio", 0)
    retraso_maximo = _num(row, "retraso_maximo", 0)
    aq_score = _num(row, "aq_score", 0)
    pm25 = _num(row, "pm25", 0)
    pm10 = _num(row, "pm10", 0)

    # Datos de sensores IoT desde ThingSpeak.
    # Estos campos pueden venir de un canal propio o público.
    iot_score = _num(row, "iot_score", 0)
    sensor_temp = _num(row, "sensor_temp", 0)
    sensor_humedad = _num(row, "sensor_humedad", 0)
    sensor_pm25 = _num(row, "sensor_pm25", 0)
    sensor_pm10 = _num(row, "sensor_pm10", 0)
    sensor_viento = _num(row, "sensor_viento", 0)

    if any(x in clima for x in ["thunderstorm", "storm"]):
        riesgo += 30
        motivos.append("tormenta")
    elif any(x in clima for x in ["rain", "drizzle", "snow"]):
        riesgo += 24
        motivos.append("precipitación")
    elif "cloud" in clima:
        riesgo += 8
        motivos.append("nubosidad")

    if any(x in descripcion for x in ["mist", "fog", "haze", "smoke"]):
        riesgo += 18
        motivos.append("niebla/bruma")

    if lluvia > 0:
        riesgo += min(18, lluvia * 6)
        motivos.append("lluvia reciente")

    if visibilidad < 3000:
        riesgo += 28
        motivos.append("visibilidad muy baja")
    elif visibilidad < 6000:
        riesgo += 18
        motivos.append("visibilidad baja")
    elif visibilidad < 9000:
        riesgo += 8
        motivos.append("visibilidad moderada")

    if viento >= 14:
        riesgo += 22
        motivos.append("viento fuerte")
    elif viento >= 9:
        riesgo += 12
        motivos.append("viento moderado")

    if rafaga >= 18:
        riesgo += 12
        motivos.append("ráfagas altas")

    if humedad >= 85 and visibilidad < 9000:
        riesgo += 8
        motivos.append("humedad + baja visibilidad")

    if nubosidad >= 85:
        riesgo += 8
        motivos.append("cielo muy cubierto")
    elif nubosidad >= 60:
        riesgo += 4
        motivos.append("cielo parcialmente cubierto")

    if total_vuelos >= 45:
        riesgo += 16
        motivos.append("alto tráfico")
    elif total_vuelos >= 20:
        riesgo += 9
        motivos.append("tráfico medio")

    if retraso_promedio >= 25:
        riesgo += 22
        motivos.append("retraso promedio alto")
    elif retraso_promedio >= 10:
        riesgo += 12
        motivos.append("retraso promedio medio")

    if retraso_maximo >= 60:
        riesgo += 8
        motivos.append("retrasos extremos")

    # OpenAQ: calidad del aire por estaciones cercanas al aeropuerto.
    # No cancela vuelos por sí sola, pero sí eleva la alerta ambiental/operativa.
    if aq_score >= 40:
        riesgo += 12
        motivos.append("OpenAQ: calidad del aire comprometida")
    elif aq_score >= 20:
        riesgo += 6
        motivos.append("OpenAQ: contaminantes moderados")

    if pm25 >= 35:
        motivos.append("OpenAQ: PM2.5 elevado")
    if pm10 >= 80:
        motivos.append("OpenAQ: PM10 elevado")

    # ThingSpeak: lectura más reciente del canal de sensores IoT.
    # El score ya resume temperatura, humedad, presión, PM, viento, etc.
    if iot_score >= 25:
        riesgo += 12
        motivos.append("ThingSpeak: sensores en alerta")
    elif iot_score >= 10:
        riesgo += 6
        motivos.append("ThingSpeak: sensores moderados")

    if sensor_viento >= 14:
        motivos.append("ThingSpeak: viento fuerte")
    if sensor_pm25 >= 35:
        motivos.append("ThingSpeak: PM2.5 alto")
    if sensor_pm10 >= 80:
        motivos.append("ThingSpeak: PM10 alto")
    if sensor_temp >= 38 or (sensor_temp > 0 and sensor_temp <= 3):
        motivos.append("ThingSpeak: temperatura extrema")
    if sensor_humedad >= 90:
        motivos.append("ThingSpeak: humedad muy alta")

    riesgo = int(min(round(riesgo), 100))
    if not motivos:
        motivos.append("condiciones normales")
    return riesgo, ", ".join(motivos[:5])


def clasificar_riesgo(riesgo):
    if riesgo >= 70:
        return "Crítico", "🔴"
    if riesgo >= 40:
        return "Precaución", "🟡"
    return "Normal", "🟢"


def estimar_retraso(row, riesgo):
    """Estimación operativa por reglas, no IA.

    Fórmula base:
    retraso estimado = 3 + 0.35 * riesgo + 0.25 * retraso_promedio_observado
    """
    retraso_promedio = _num(row, "retraso_promedio", 0)
    total_vuelos = _num(row, "total_vuelos", 0)
    iot_score = _num(row, "iot_score", 0)
    aq_score = _num(row, "aq_score", 0)
    extra_trafico = 5 if total_vuelos >= 45 else 2 if total_vuelos >= 20 else 0
    extra_ambiental = 3 if (iot_score >= 25 or aq_score >= 40) else 1 if (iot_score >= 10 or aq_score >= 20) else 0
    return int(round(3 + (0.35 * riesgo) + (0.25 * retraso_promedio) + extra_trafico + extra_ambiental))


def generar_predicciones(df_resumen):
    if df_resumen.empty:
        return pd.DataFrame()

    pred = df_resumen.copy()
    riesgos = pred.apply(calcular_riesgo, axis=1, result_type="expand")
    pred["riesgo"] = riesgos[0].astype(int)
    pred["motivo_riesgo"] = riesgos[1]

    niveles = pred["riesgo"].apply(clasificar_riesgo)
    pred["nivel_operativo"] = niveles.apply(lambda x: x[0])
    pred["semaforo"] = niveles.apply(lambda x: x[1])
    pred["probabilidad_retraso"] = pred["riesgo"].astype(int).clip(0, 100)
    pred["retraso_estimado_min"] = pred.apply(lambda row: estimar_retraso(row, row["riesgo"]), axis=1)
    return pred.sort_values("riesgo", ascending=False)
