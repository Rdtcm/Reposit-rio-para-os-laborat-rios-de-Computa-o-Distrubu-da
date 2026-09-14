FROM ubuntu:22.04

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    openssh-server openmpi-bin libopenmpi-dev python3 python3-pip && \
    python3 -m pip install --no-cache-dir mpi4py && \
    useradd -m -s /bin/bash mpiuser && \
    mkdir -p /run/sshd /home/mpiuser/.ssh && \
    ssh-keygen -q -t ed25519 -N '' -f /home/mpiuser/.ssh/id_ed25519 && \
    cat /home/mpiuser/.ssh/id_ed25519.pub > /home/mpiuser/.ssh/authorized_keys && \
    printf 'Host *\n  StrictHostKeyChecking no\n  UserKnownHostsFile=/dev/null\n' > /home/mpiuser/.ssh/config && \
    chown -R mpiuser:mpiuser /home/mpiuser/.ssh && chmod 700 /home/mpiuser/.ssh && \
    chmod 600 /home/mpiuser/.ssh/authorized_keys /home/mpiuser/.ssh/config

RUN python3 -m pip install --no-cache-dir numpy reportlab pypdf

WORKDIR /home/mpiuser
COPY hosts /home/mpiuser/hosts
COPY *.py /home/mpiuser/
CMD ["/usr/sbin/sshd", "-D"]
