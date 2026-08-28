#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if ! docker compose ps >/dev/null 2>&1; then
  docker compose up -d --build
fi

for file in run_lab1.sh hosts exercicio1_figlet_distribuido.c exercicio2_hostname_mpi.c exercicio3_alfabeto_cluster.c; do
  if [ -f "$file" ]; then
    docker cp "$file" master:/home/mpiuser/"$file" >/dev/null 2>&1 || true
  fi
done

docker compose exec -T master bash -lc 'sudo -u mpiuser bash -lc "cd /home/mpiuser && chmod +x run_lab1.sh && ./run_lab1.sh"'
