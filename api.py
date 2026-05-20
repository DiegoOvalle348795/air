import os
import ssl
import asyncio
from pathlib import Path

import aiohttp
import certifi
from dotenv import load_dotenv


def _ssl_connector():
    """CA bundle de certifi: evita SSLCertVerificationError en macOS/Python.org."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    return aiohttp.TCPConnector(ssl=ctx)

# Ruta fija al .env del proyecto: Streamlit/IDE a veces arrancan con otro cwd y
# load_dotenv() sin argumentos no encuentra el archivo.
_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")


def _env_api_key(name: str):
    """Lee claves de API: None si falta o si el valor es solo espacios (o vacío)."""
    raw = os.getenv(name)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None


API_KEY = _env_api_key("API_KEY")
AIRLABS_API_KEY = _env_api_key("AIRLABS_API_KEY")
OPENAQ_API_KEY = _env_api_key("OPENAQ_API_KEY")
OPENAQ_RADIUS_M = int(os.getenv("OPENAQ_RADIUS_M", "25000"))
THINGSPEAK_CHANNEL_ID = os.getenv("THINGSPEAK_CHANNEL_ID", "9")
THINGSPEAK_READ_API_KEY = os.getenv("THINGSPEAK_READ_API_KEY")
THINGSPEAK_RESULTS = int(os.getenv("THINGSPEAK_RESULTS", "25"))

if API_KEY is None or AIRLABS_API_KEY is None:
    print("Missing api key values. Configure API_KEY and AIRLABS_API_KEY in your .env file.")


async def _leer_json(response):
    try:
        return await response.json(content_type=None)
    except Exception:
        texto = await response.text()
        return {"error": texto[:500]}


async def obtener_clima(session, ciudad):
    if API_KEY is None:
        return {"ciudad": ciudad["nombre"], "error": "Missing API_KEY"}
    try:
        lat = ciudad["lat"]
        lon = ciudad["lon"]
        url = (
            f"https://api.openweathermap.org/data/2.5/weather"
            f"?lat={lat}"
            f"&lon={lon}"
            f"&units=metric"
            f"&appid={API_KEY}"
        )

        async with session.get(url) as response:
            data = await _leer_json(response)
            if str(data.get("cod", "200")) not in ("200", "0"):
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": ciudad.get("iata"),
                    "lat": ciudad.get("lat"),
                    "lon": ciudad.get("lon"),
                    "error": data.get("message", str(data)),
                }
            main = data.get("main") or {}
            weather0 = (data.get("weather") or [{}])[0]
            wind = data.get("wind") or {}
            clouds = data.get("clouds") or {}
            rain = data.get("rain") or {}
            return {
                "ciudad": ciudad["nombre"],
                "iata": ciudad.get("iata"),
                "lat": ciudad.get("lat"),
                "lon": ciudad.get("lon"),
                "temperatura": main.get("temp"),
                "sensacion_termica": main.get("feels_like"),
                "humedad": main.get("humidity"),
                "presion": main.get("pressure"),
                "visibilidad": data.get("visibility"),
                "viento_velocidad": wind.get("speed"),
                "viento_rafaga": wind.get("gust"),
                "viento_direccion": wind.get("deg"),
                "nubosidad": clouds.get("all"),
                "lluvia_1h": rain.get("1h", 0),
                "clima": weather0.get("main"),
                "descripcion": weather0.get("description"),
            }

    except Exception as e:
        print(f"error en {ciudad} con error {e}")
        return {
            "ciudad": ciudad["nombre"],
            "iata": ciudad.get("iata"),
            "lat": ciudad.get("lat"),
            "lon": ciudad.get("lon"),
            "error": str(e),
        }


async def obtener_climas(ciudades):
    async with aiohttp.ClientSession(connector=_ssl_connector()) as session:
        tareas = [obtener_clima(session, ciudad) for ciudad in ciudades]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        return resultados


def _retraso_total(ruta):
    valores = [
        ruta.get("delayed"),
        ruta.get("dep_delayed"),
        ruta.get("arr_delayed"),
    ]
    numericos = []
    for valor in valores:
        try:
            if valor is not None:
                numericos.append(float(valor))
        except (TypeError, ValueError):
            pass
    return max(numericos) if numericos else 0


async def obtener_vuelos(session, ciudad):
    if AIRLABS_API_KEY is None:
        return {"ciudad": ciudad["nombre"], "error": "Missing AIRLABS_API_KEY"}
    try:
        iata = ciudad["iata"]
        url = (
            f"https://airlabs.co/api/v9/schedules"
            f"?api_key={AIRLABS_API_KEY}"
            f"&dep_iata={iata}"
        )

        async with session.get(url) as response:
            data = await _leer_json(response)
            if data.get("error"):
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": iata,
                    "error": str(data["error"]),
                }

            rutas = data.get("response")
            if rutas is None:
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": iata,
                    "error": data.get("message", "Sin campo response en la respuesta"),
                }
            if not isinstance(rutas, list):
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": iata,
                    "error": f"response inesperado: {type(rutas).__name__}",
                }

            return {
                "ciudad": ciudad["nombre"],
                "iata": iata,
                "total_rutas": len(rutas),
                "rutas": [
                    {
                        "origen": ruta.get("dep_iata"),
                        "destino": ruta.get("arr_iata"),
                        "aerolinea": ruta.get("airline_iata"),
                        "vuelo": ruta.get("flight_iata"),
                        "estado": ruta.get("status"),
                        "hora_salida": ruta.get("dep_time"),
                        "hora_llegada": ruta.get("arr_time"),
                        "retraso": _retraso_total(ruta),
                        "retraso_salida": ruta.get("dep_delayed") or 0,
                        "retraso_llegada": ruta.get("arr_delayed") or 0,
                        "duracion": ruta.get("duration"),
                        "avion": ruta.get("aircraft_icao"),
                    }
                    for ruta in rutas
                ],
            }

    except Exception as e:
        print(f"error vuelos {ciudad} con error {e}")
        return {"ciudad": ciudad["nombre"], "iata": ciudad.get("iata"), "error": str(e)}


async def obtener_todos_vuelos(ciudades):
    async with aiohttp.ClientSession(connector=_ssl_connector()) as session:
        tareas = [obtener_vuelos(session, ciudad) for ciudad in ciudades]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        return resultados


def _openaq_headers():
    headers = {"Accept": "application/json"}
    if OPENAQ_API_KEY:
        headers["X-API-Key"] = OPENAQ_API_KEY
    return headers


def _parametro_openaq(registro):
    """Intenta obtener el nombre del contaminante en respuestas v3 o variantes.

    OpenAQ v3 regresa el valor y sensor; algunas respuestas incluyen el parámetro,
    otras no. Por eso dejamos un nombre seguro basado en sensorsId si no viene.
    """
    for llave in ("parameter", "parameterName", "parameters", "parameter_name"):
        valor = registro.get(llave)
        if isinstance(valor, str):
            return valor.lower()
        if isinstance(valor, dict):
            nombre = valor.get("name") or valor.get("displayName") or valor.get("parameter")
            if nombre:
                return str(nombre).lower()
    sensor = registro.get("sensorsId") or registro.get("sensorId") or registro.get("sensor_id")
    return f"sensor_{sensor}" if sensor is not None else "desconocido"


async def obtener_openaq_ciudad(session, ciudad):
    if OPENAQ_API_KEY is None:
        return {
            "ciudad": ciudad["nombre"],
            "iata": ciudad.get("iata"),
            "error": "Missing OPENAQ_API_KEY. Crea una key en OpenAQ y agrega OPENAQ_API_KEY al .env",
        }

    try:
        lat = ciudad["lat"]
        lon = ciudad["lon"]
        headers = _openaq_headers()
        base = "https://api.openaq.org/v3"
        params = f"coordinates={lat:.4f},{lon:.4f}&radius={OPENAQ_RADIUS_M}&limit=1"
        url_locations = f"{base}/locations?{params}"

        async with session.get(url_locations, headers=headers) as response:
            data_locations = await _leer_json(response)
            if response.status >= 400:
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": ciudad.get("iata"),
                    "error": data_locations.get("detail", data_locations.get("error", str(data_locations))),
                }

        ubicaciones = data_locations.get("results") or []
        if not ubicaciones:
            return {
                "ciudad": ciudad["nombre"],
                "iata": ciudad.get("iata"),
                "lat": lat,
                "lon": lon,
                "error": f"Sin estaciones OpenAQ en radio de {OPENAQ_RADIUS_M} m",
            }

        ubicacion = ubicaciones[0]
        location_id = ubicacion.get("id")
        location_name = ubicacion.get("name") or ubicacion.get("locality") or f"location_{location_id}"
        if location_id is None:
            return {"ciudad": ciudad["nombre"], "iata": ciudad.get("iata"), "error": "Ubicación OpenAQ sin id"}

        url_latest = f"{base}/locations/{location_id}/latest?limit=100"
        async with session.get(url_latest, headers=headers) as response:
            data_latest = await _leer_json(response)
            if response.status >= 400:
                return {
                    "ciudad": ciudad["nombre"],
                    "iata": ciudad.get("iata"),
                    "location_id": location_id,
                    "error": data_latest.get("detail", data_latest.get("error", str(data_latest))),
                }

        mediciones = []
        for registro in data_latest.get("results") or []:
            coords = registro.get("coordinates") or {}
            dt = registro.get("datetime") or {}
            mediciones.append(
                {
                    "ciudad": ciudad["nombre"],
                    "iata": ciudad.get("iata"),
                    "location_id": location_id,
                    "location_name": location_name,
                    "parametro": _parametro_openaq(registro),
                    "valor": registro.get("value"),
                    "unidad": registro.get("unit") or registro.get("units") or "",
                    "fecha_utc": dt.get("utc") if isinstance(dt, dict) else None,
                    "fecha_local": dt.get("local") if isinstance(dt, dict) else None,
                    "sensor_id": registro.get("sensorsId") or registro.get("sensorId"),
                    "lat": coords.get("latitude", lat),
                    "lon": coords.get("longitude", lon),
                }
            )

        return {
            "ciudad": ciudad["nombre"],
            "iata": ciudad.get("iata"),
            "location_id": location_id,
            "location_name": location_name,
            "mediciones": mediciones,
        }
    except Exception as e:
        return {"ciudad": ciudad["nombre"], "iata": ciudad.get("iata"), "error": str(e)}


async def obtener_openaq_ciudades(ciudades):
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, connector=_ssl_connector()) as session:
        tareas = [obtener_openaq_ciudad(session, ciudad) for ciudad in ciudades]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        return resultados


async def obtener_thingspeak():
    """Lee datos de un canal público o privado de ThingSpeak.

    Variables .env opcionales:
    - THINGSPEAK_CHANNEL_ID: por defecto 9, canal público de ejemplo.
    - THINGSPEAK_READ_API_KEY: solo necesario si el canal es privado.
    - THINGSPEAK_RESULTS: cantidad de lecturas a descargar.
    """
    try:
        params = f"results={THINGSPEAK_RESULTS}"
        if THINGSPEAK_READ_API_KEY:
            params += f"&api_key={THINGSPEAK_READ_API_KEY}"
        url = f"https://api.thingspeak.com/channels/{THINGSPEAK_CHANNEL_ID}/feeds.json?{params}"

        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout, connector=_ssl_connector()) as session:
            async with session.get(url) as response:
                data = await _leer_json(response)
                if response.status >= 400:
                    return {"error": data.get("error", str(data)), "channel_id": THINGSPEAK_CHANNEL_ID}

        channel = data.get("channel") or {}
        feeds = data.get("feeds") or []
        field_names = {
            key: value for key, value in channel.items()
            if key.startswith("field") and value
        }

        registros = []
        for feed in feeds:
            fila = {
                "channel_id": THINGSPEAK_CHANNEL_ID,
                "channel_name": channel.get("name", f"ThingSpeak {THINGSPEAK_CHANNEL_ID}"),
                "created_at": feed.get("created_at"),
                "entry_id": feed.get("entry_id"),
            }
            for field_key, field_label in field_names.items():
                fila[field_label] = feed.get(field_key)
            registros.append(fila)

        return {
            "channel_id": THINGSPEAK_CHANNEL_ID,
            "channel_name": channel.get("name", f"ThingSpeak {THINGSPEAK_CHANNEL_ID}"),
            "field_names": field_names,
            "registros": registros,
        }
    except Exception as e:
        return {"error": str(e), "channel_id": THINGSPEAK_CHANNEL_ID}
