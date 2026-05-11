from mpi4py import MPI
import asyncio
from api import obtener_climas, obtener_openaq_ciudades, obtener_thingspeak, obtener_todos_vuelos
from data import cities


def run_mpi():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    ciudades = cities[rank::size]

    resultados_clima = asyncio.run(obtener_climas(ciudades))
    resultados_vuelos = asyncio.run(obtener_todos_vuelos(ciudades))
    resultados_openaq = asyncio.run(obtener_openaq_ciudades(ciudades))

    print(f"Proceso {rank}/{size}")
    print("Clima:", resultados_clima)
    print("Vuelos:", resultados_vuelos)
    print("OpenAQ:", resultados_openaq)

    if rank == 0:
        resultado_thingspeak = asyncio.run(obtener_thingspeak())
        print("ThingSpeak:", resultado_thingspeak)


if __name__ == "__main__":
    run_mpi()
