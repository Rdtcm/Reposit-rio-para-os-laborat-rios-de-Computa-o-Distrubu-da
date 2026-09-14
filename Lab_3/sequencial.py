"""Baseline sequencial para a multiplicacao de matrizes do Exercicio 1."""
from __future__ import annotations

import argparse
from time import perf_counter
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    a = rng.random((args.n, args.n))
    b = rng.random((args.n, args.n))
    b_t = b.T
    start = perf_counter()
    c = a @ b_t
    elapsed_ms = (perf_counter() - start) * 1000
    print(f"Matriz {args.n}x{args.n}")
    print(f"Checksum de C: {c.sum():.6f}")
    print(f"Tempo sequencial: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()
