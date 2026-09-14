"""Versao com threads locais para a multiplicacao de matrizes."""
from __future__ import annotations

import argparse
import threading
from time import perf_counter
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260913)
    args = parser.parse_args()
    if args.threads <= 0:
        raise ValueError("threads deve ser positivo")
    rng = np.random.default_rng(args.seed)
    a = rng.random((args.n, args.n))
    b = rng.random((args.n, args.n))
    b_t = b.T
    c = np.empty((args.n, args.n))

    def work(first: int, last: int) -> None:
        c[first:last] = a[first:last] @ b_t

    start = perf_counter()
    workers = []
    for worker in range(args.threads):
        first = worker * args.n // args.threads
        last = (worker + 1) * args.n // args.threads
        thread = threading.Thread(target=work, args=(first, last))
        workers.append(thread)
        thread.start()
    for thread in workers:
        thread.join()
    elapsed_ms = (perf_counter() - start) * 1000
    print(f"Matriz {args.n}x{args.n}; threads: {args.threads}")
    print(f"Checksum de C: {c.sum():.6f}")
    print(f"Tempo multithreaded: {elapsed_ms:.2f} ms")


if __name__ == "__main__":
    main()
