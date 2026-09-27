FROM ubuntu:22.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openssh-server openmpi-bin libopenmpi-dev python3 python3-numpy python3-mpi4py && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash mpiuser && \
    mkdir -p /run/sshd /home/mpiuser/.ssh && \
    ssh-keygen -q -t ed25519 -N '' -f /home/mpiuser/.ssh/id_ed25519 && \
    cat /home/mpiuser/.ssh/id_ed25519.pub > /home/mpiuser/.ssh/authorized_keys && \
    printf 'Host master worker1 worker2 worker3\n  StrictHostKeyChecking no\n  UserKnownHostsFile=/dev/null\n  LogLevel ERROR\n' > /home/mpiuser/.ssh/config && \
    chown -R mpiuser:mpiuser /home/mpiuser/.ssh && \
    chmod 700 /home/mpiuser/.ssh && chmod 600 /home/mpiuser/.ssh/*

COPY --chown=mpiuser:mpiuser hosts /home/mpiuser/hosts
WORKDIR /home/mpiuser/lab
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
CMD ["/usr/sbin/sshd", "-D", "-e"]
