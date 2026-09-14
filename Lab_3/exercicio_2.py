"""Estimativa distribuida de pi pelo metodo de Monte Carlo.

Uso: mpirun --hostfile hosts -np 4 python3 exercicio_2.py --points 10000000
"""
from __future__ import annotations

import argparse
import random

from mpi4py import MPI


def count_inside(samples: int, seed: int) -> int:
    rng = random.Random(seed)
    inside = 0
    for _ in range(samples):
        x, y = rng.random(), rng.random()
        if x * x + y * y <= 1.0:
            inside += 1
    return inside


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=int, default=10_000_000)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    if args.points <= 0:
        raise ValueError("points deve ser positivo")
    comm = MPI.COMM_WORLD
    rank, size = comm.Get_rank(), comm.Get_size()
    local_points = (rank + 1) * args.points // size - rank * args.points // size
    comm.Barrier()
    start = MPI.Wtime()
    local_inside = count_inside(local_points, args.seed + rank)
    total_inside = comm.reduce(local_inside, op=MPI.SUM, root=0)
    elapsed_ms = (MPI.Wtime() - start) * 1000
    if rank == 0:
        estimate = 4.0 * total_inside / args.points
        print(f"Pontos: {args.points}; processos MPI: {size}")
        print(f"Pontos internos acumulados: {total_inside}")
        print(f"PI aproximado: {estimate:.6f}")
        print(f"Tempo distribuido MPI: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()
