#include <mpi.h>
#include <stdio.h>
#include <unistd.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    char hostname[256];
    gethostname(hostname, sizeof(hostname));

    const char *palavras[5] = {"Olá", "Mack,", "sou", "o", "Ryan"};

    if (size < 5) {
        if (rank == 0) {
            fprintf(stderr, "Este exercício requer pelo menos 5 processos MPI.\n");
        }
        MPI_Finalize();
        return 1;
    }

    if (rank < 5) {
        printf("[Rank %d | %s] %s\n", rank, hostname, palavras[rank]);
    }

    MPI_Finalize();
    return 0;
}
