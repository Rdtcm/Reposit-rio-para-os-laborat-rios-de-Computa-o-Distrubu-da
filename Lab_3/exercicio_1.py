from mpi4py import MPI
import time
import random


N = 1000
C = [[0]*N for _ in range(N)]

def main():

    # 1. Inicializa o ambiente de execução MPI (gerenciado ao importar mpi4py)
    comm = MPI.COMM_WORLD
    # Obtenção do tamanho do comunicador e do rank do processo atual
    size = comm.Get_size()
    rank = comm.Get_rank()
    print(f"Processo {rank} de {size}")

    if rank == 0:
        A = [[random.random() for _ in range(N)] for _ in range(N)]
        B = [[random.random() for _ in range(N)] for _ in range(N)]
    else:
        A = None
        B = None

    comm.Barrier()
    inicio_tempo = MPI.Wtime()


    A = comm.bcast(A, root=0)
    B = comm.bcast(B, root=0)

    # separando intervalos de cada processo
    inicio = rank * (N // size)
    fim = N if rank == size - 1 else (rank + 1) * (N // size)

    quantidade_linhas = fim - inicio
    C_local = [[0] * N for _ in range(quantidade_linhas)]

    # criando a matriz e calculando
    for i in range(inicio, fim):
        linha_local = i - inicio
        for j in range(N):
            C_local[linha_local][j] = 0
            for k in range(N):
                C_local[linha_local][j] += A[i][k] * B[k][j]

    # juntando o resultado de cada processo e enviando ao processo root
    partes = comm.gather(C_local, root=0)

    fim_tempo = MPI.Wtime()  

    if rank == 0:
        # construir a matriz final fazendo merge com as matrizes C_locais
        C = []

        for parte in partes:
            C.extend(parte)

        tempo = (fim_tempo - inicio_tempo)

        print(C)
        print(f"Tempo MPI: {tempo:.2f} s")

    MPI.Finalize()

            


if __name__ == "__main__":
    main()



    















