FROM ubuntu:22.04

RUN apt update && \
    apt install -y \
    python3 \
    python3-pip \
    openmpi-bin \
    libopenmpi-dev && \
    python3 -m pip install --no-cache-dir mpi4py && \
    useradd -m -s /bin/bash mpiuser && \
    echo "mpiuser:mpi123" | chpasswd && \
    mkdir /var/run/sshd

WORKDIR /app

COPY main.py /app/main.py

CMD ["mpirun", "--allow-run-as-root", "-np", "4", "python3", "/app/main.py"]