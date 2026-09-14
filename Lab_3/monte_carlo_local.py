"""Baselines local sequencial e com threads para o Exercicio 2."""
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
    parser.add_argument("--mode", choices=("sequential", "threads"), required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    start = perf_counter()
    if args.mode == "sequential":
        inside = count_inside(args.points, args.seed)
    else:
        values = [0] * args.threads
        def work(index: int) -> None:
            count = (index + 1) * args.points // args.threads - index * args.points // args.threads
            values[index] = count_inside(count, args.seed + index)
        jobs = [threading.Thread(target=work, args=(index,)) for index in range(args.threads)]
        for job in jobs:
            job.start()
        for job in jobs:
            job.join()
        inside = sum(values)
    elapsed_ms = (perf_counter() - start) * 1000
    label = "sequencial" if args.mode == "sequential" else "multithreaded"
    print(f"Pontos: {args.points}")
    print(f"Pontos internos: {inside}")
    print(f"PI aproximado: {4.0 * inside / args.points:.6f}")
    print(f"Tempo {label}: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()
