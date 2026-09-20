"""Baseline sequencial para a estimativa de PI do Exercicio 2.

Uso: python sequencial_pi.py --points 10000000
"""
from __future__ import annotations

import argparse
import random
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
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    if args.points <= 0:
        raise ValueError("points deve ser positivo")

    start = perf_counter()
    inside = count_inside(args.points, args.seed)
    elapsed_ms = (perf_counter() - start) * 1000

    print(f"Pontos: {args.points}")
    print(f"Pontos internos: {inside}")
    print(f"PI aproximado: {4.0 * inside / args.points:.6f}")
    print(f"Tempo sequencial: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()