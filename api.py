import os
import aiohttp
import asyncio
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
AIRLABS_API_KEY = os.getenv("AIRLABS_API_KEY")

if API_KEY is None or AIRLABS_API_KEY is None:
    print("Missing api key values")
    exit(1)


async def obtener_clima(session, ciudad):
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
            return {
                "ciudad": ciudad["nombre"],
                "temperatura": data["main"]["temp"],
                "humedad": data["main"]["humidity"],
                "presion": data["main"]["pressure"],
                "visibilidad": data.get("visibility"),
                "viento_velocidad": data["wind"]["speed"],
                "viento_direccion": data["wind"]["deg"],
                "clima": data["weather"][0]["main"],
                "descripcion": data["weather"][0]["description"],
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
    try:
        iata = ciudad["iata"]
        url = (
            f"https://airlabs.co/api/v9/schedules"
            f"?api_key={AIRLABS_API_KEY}"
            f"&dep_iata={iata}"
        )

        async with session.get(url) as response:
            data = await response.json()
            if "response" not in data:
                return {
                    "ciudad": ciudad["nombre"],
                    "error": data.get("error", "No data"),
                }

            rutas = data["response"]

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
