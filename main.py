from mpi4py import MPI
import asyncio
from api import obtener_climas, obtener_todos_vuelos

cities = [
    {
        "nombre": "Ciudad de México",
        "iata": "MEX",
        "lat": 19.4326,
        "lon": -99.1332,
    },
    {
        "nombre": "Monterrey, Nuevo León",
        "iata": "MTY",
        "lat": 25.6866,
        "lon": -100.3161,
    },
    {
        "nombre": "Guadalajara, Jalisco",
        "iata": "GDL",
        "lat": 20.6597,
        "lon": -103.3496,
    },
    {
        "nombre": "Querétaro",
        "iata": "QRO",
        "lat": 20.5888,
        "lon": -100.3899,
    },
    {
        "nombre": "San Luis Potosí",
        "iata": "SLP",
        "lat": 22.1565,
        "lon": -100.9855,
    },
    {
        "nombre": "Puebla",
        "iata": "PBC",
        "lat": 19.0414,
        "lon": -98.2063,
    },
    {
        "nombre": "Tijuana",
        "iata": "TIJ",
        "lat": 32.5149,
        "lon": -117.0382,
    },
    {
        "nombre": "Ciudad Juárez",
        "iata": "CJS",
        "lat": 31.6904,
        "lon": -106.4245,
    },
    {
        "nombre": "León, Guanajuato",
        "iata": "BJX",
        "lat": 21.1220,
        "lon": -101.6823,
    },
    {
        "nombre": "Torreón, Coahuila",
        "iata": "TRC",
        "lat": 25.5428,
        "lon": -103.4068,
    },
    {
        "nombre": "Chihuahua",
        "iata": "CUU",
        "lat": 28.6353,
        "lon": -106.0889,
    },
]

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
ciudades = cities[rank::size]

resultados = asyncio.run(obtener_climas(ciudades))
resultado_vuelos = asyncio.run(obtener_todos_vuelos(ciudades))

