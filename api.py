import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")

if API_KEY is None or AIRLABS_API_KEY is None:
    print("Missing api key values. Configure API_KEY and AIRLABS_API_KEY in your .env file.")


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
            data = await response.json()
            if str(data.get("cod", "200")) not in ("200", "0"):
                return {
                    "ciudad": ciudad["nombre"],
                    "error": data.get("message", str(data)),
                }
            main = data.get("main") or {}
            weather0 = (data.get("weather") or [{}])[0]
            wind = data.get("wind") or {}
            return {
                "ciudad": ciudad["nombre"],
                "temperatura": main.get("temp"),
                "humedad": main.get("humidity"),
                "presion": main.get("pressure"),
                "visibilidad": data.get("visibility"),
                "viento_velocidad": wind.get("speed"),
                "viento_direccion": wind.get("deg"),
                "clima": weather0.get("main"),
                "descripcion": weather0.get("description"),
            }

    except Exception as e:
        print(f"error en {ciudad} con error {e}")
        return {"ciudad": ciudad["nombre"], "error": str(e)}


async def obtener_climas(ciudades):
    async with aiohttp.ClientSession() as session:

        tareas = [obtener_clima(session, ciudad) for ciudad in ciudades]

        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        return resultados


# vuelos papupro
"""
async def obtener_vuelos(session, ciudad):

    try:

        iata = ciudad["iata"]
        rutas = []
        page = 1

        while True:

            url = (
                f"https://airlabs.co/api/v9/routes"
                f"?api_key={AIRLABS_API_KEY}"
                f"&dep_iata={iata}"
                f"&page={page}"
            )

            async with session.get(url) as response:

                data = await response.json()
                nuevas_rutas = data.get("response", [])
                
                if not nuevas_rutas:
                    break

                for ruta in nuevas_rutas:
                    if ruta not in rutas:
                        rutas.append(ruta)

                page += 1

        return {
            "ciudad": ciudad["nombre"],
            "iata": iata,
            "total_rutas": len(rutas),

            "destinos": [
                ruta["arr_iata"]
                for ruta in rutas
            ]
        }

    except Exception as e:
        print(f"error vuelos {ciudad} -> {e}")

        return {
            "ciudad": ciudad["nombre"],
            "error": str(e)
        }
"""


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
            data = await response.json()
            if data.get("error"):
                return {
                    "ciudad": ciudad["nombre"],
                    "error": str(data["error"]),
                }

            rutas = data.get("response")
            if rutas is None:
                return {
                    "ciudad": ciudad["nombre"],
                    "error": data.get("message", "Sin campo response en la respuesta"),
                }
            if not isinstance(rutas, list):
                return {
                    "ciudad": ciudad["nombre"],
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
                        "retraso": ruta.get("delayed") or 0,
                    }
                    for ruta in rutas
                ],
            }

    except Exception as e:
        print(f"error vuelos {ciudad} con error {e}")
        return {"ciudad": ciudad["nombre"], "error": str(e)}


async def obtener_todos_vuelos(ciudades):
    async with aiohttp.ClientSession() as session:

        tareas = [obtener_vuelos(session, ciudad) for ciudad in ciudades]

        resultados = await asyncio.gather(*tareas, return_exceptions=True)
        return resultados
