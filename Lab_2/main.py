from mpi4py import MPI
import random
# Inicialização do MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()
#
# Função para gerar logs
#
def gerar_logs(qtd):
    ips = [f"192.168.1.{i}" for i in range(2,254)]
    endpoints = [
    "/",
    "/login",
    "/products",
    "/cart",
    "/checkout",
    "/api/users",
    "/api/orders"
    ]
    metodos = ["GET", "POST"]
    status = ["200", "200", "200", "404", "500"]
    logs = []

    for _ in range(qtd):
        ip = random.choice(ips)
        endpoint = random.choice(endpoints)
        metodo = random.choice(metodos)
        codigo_status = random.choice(status)
        logs.append(f"{ip} {metodo} {endpoint} {codigo_status}")

    return logs


#
# Processo 0 gera o dataset
#
logs_divididos = None
TOTAL_LOGS = 100000
if rank == 0:
    print("\nGerando dataset de logs...\n")
    logs = gerar_logs(TOTAL_LOGS)

    if TOTAL_LOGS % size != 0:
        raise ValueError("TOTAL_LOGS deve ser divisível pela quantidade de processos MPI.")

    tamanho_parte = TOTAL_LOGS // size
    logs_divididos = [
        logs[inicio:inicio + tamanho_parte]
        for inicio in range(0, TOTAL_LOGS, tamanho_parte)
    ]

#
# Distribuição usando Scatter
#
logs_locais = comm.scatter(logs_divididos, root=0)

#
# Processamento local em cada nó
#
erros = 0
for log in logs_locais:
    campos = log.split()
    codigo_status = campos[-1]
    if codigo_status in {"404", "500"}:
        erros += 1

mensagem = (
    f"Processo {rank} analisou {len(logs_locais)} linhas "
    f"e encontrou {erros} erros."
)
#
# Nós Master
# Imprime os resultados de cada nó worker e seu também
#
# A variável 'logs_locais' representa a fatia recebida e 'erros' o contador
if rank == 0:
    mensagens = [mensagem]
    for origem in range(1, size):
        mensagens.append(comm.recv(source=origem, tag=origem))

    for resultado in mensagens:
        print(resultado)
else:
    comm.send(mensagem, dest=0, tag=rank)
