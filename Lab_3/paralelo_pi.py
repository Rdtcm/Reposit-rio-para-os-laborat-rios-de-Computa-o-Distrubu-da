"""Baseline com threads locais para a estimativa de PI do Exercicio 2.

Uso: python paralelo_pi.py --points 10000000 --threads 4
"""
from __future__ import annotations

import argparse
import random
import threading
from time import perf_counter


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
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    if args.points <= 0:
        raise ValueError("points deve ser positivo")
    if args.threads <= 0:
        raise ValueError("threads deve ser positivo")

    # mesma particao usada na versao MPI: distribui o resto automaticamente
    valores = [0] * args.threads

    def trabalho(indice: int) -> None:
        inicio = indice * args.points // args.threads
        fim = (indice + 1) * args.points // args.threads
        valores[indice] = count_inside(fim - inicio, args.seed + indice)

    start = perf_counter()
    threads = [
        threading.Thread(target=trabalho, args=(i,)) for i in range(args.threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    inside = sum(valores)
    elapsed_ms = (perf_counter() - start) * 1000

    print(f"Pontos: {args.points}; threads: {args.threads}")
    print(f"Pontos internos: {inside}")
    print(f"PI aproximado: {4.0 * inside / args.points:.6f}")
    print(f"Tempo multithreaded: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()