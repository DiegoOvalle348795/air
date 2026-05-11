from mpi4py import MPI
import asyncio
from api import obtener_climas, obtener_todos_vuelos
from data import cities


def run_mpi():
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    ciudades = cities[rank::size]

    resultados = asyncio.run(obtener_climas(ciudades))
    resultado_vuelos = asyncio.run(obtener_todos_vuelos(ciudades))

    print(f"Proceso {rank}/{size}")
    print("Clima:", resultados)
    print("Vuelos:", resultado_vuelos)


if __name__ == "__main__":
    run_mpi()
