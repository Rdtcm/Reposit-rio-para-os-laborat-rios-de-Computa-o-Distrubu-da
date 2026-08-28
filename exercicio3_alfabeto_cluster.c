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

    if (size < 26) {
        if (rank == 0) {
            fprintf(stderr, "Este exercício requer pelo menos 26 processos MPI.\n");
        }
        MPI_Finalize();
        return 1;
    }

    char letra = (char)('A' + rank);
    printf("[Rank %d | %s] %c\n", rank, hostname, letra);

    MPI_Finalize();
    return 0;
}
