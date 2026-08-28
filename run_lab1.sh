#!/bin/bash
set -euo pipefail

if [ ! -d /home/mpiuser ]; then
  echo "Este script deve ser executado dentro do contêiner master do cluster ou via ./run_lab.sh no host." >&2
  exit 1
fi

HOME_DIR="/home/mpiuser"
cd "$HOME_DIR"

for node in worker1 worker2 worker3; do
  scp -o StrictHostKeyChecking=no "$HOME_DIR/hosts" "$node:$HOME_DIR/hosts" >/dev/null 2>&1 || true
done

mpicc -O2 /home/mpiuser/exercicio1_figlet_distribuido.c -o /home/mpiuser/exercicio1_figlet_distribuido
mpicc -O2 /home/mpiuser/exercicio2_hostname_mpi.c -o /home/mpiuser/exercicio2_hostname_mpi
mpicc -O2 /home/mpiuser/exercicio3_alfabeto_cluster.c -o /home/mpiuser/exercicio3_alfabeto_cluster

for node in worker1 worker2 worker3; do
  scp -o StrictHostKeyChecking=no /home/mpiuser/exercicio1_figlet_distribuido "$node:$HOME_DIR/exercicio1_figlet_distribuido" >/dev/null 2>&1 || true
  scp -o StrictHostKeyChecking=no /home/mpiuser/exercicio2_hostname_mpi "$node:$HOME_DIR/exercicio2_hostname_mpi" >/dev/null 2>&1 || true
  scp -o StrictHostKeyChecking=no /home/mpiuser/exercicio3_alfabeto_cluster "$node:$HOME_DIR/exercicio3_alfabeto_cluster" >/dev/null 2>&1 || true
done

echo "=== Exercício 1 – Frase distribuída em texto comum ==="
for i in $(seq 1 5); do
  echo "Execução $i"
  mpirun --allow-run-as-root --hostfile "$HOME_DIR/hosts" --oversubscribe -np 5 /home/mpiuser/exercicio1_figlet_distribuido
  echo
  echo "---"
done

echo "=== Exercício 2 – Descobrir cores e threads ==="
mpirun --allow-run-as-root --hostfile "$HOME_DIR/hosts" -np 1 /home/mpiuser/exercicio2_hostname_mpi
mpirun --allow-run-as-root --hostfile "$HOME_DIR/hosts" -np 2 /home/mpiuser/exercicio2_hostname_mpi
mpirun --allow-run-as-root --hostfile "$HOME_DIR/hosts" --oversubscribe -np 16 /home/mpiuser/exercicio2_hostname_mpi

echo "=== Exercício 3 – Cluster soletrando o alfabeto ==="
mpirun --allow-run-as-root --hostfile "$HOME_DIR/hosts" --oversubscribe -np 26 /home/mpiuser/exercicio3_alfabeto_cluster
