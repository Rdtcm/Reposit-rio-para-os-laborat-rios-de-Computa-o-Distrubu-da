# Relatorio - Multiplicacao de Matrizes e Metodo de Monte Carlo com MPI

**Aluno:** Ryan Ledo  
**RA:** 10352727  
**Instituicao:** FCI - Mackenzie  
**Turma:** 06N  
**Disciplina:** Computacao Distribuida  
**Laboratorio:** Laboratório 3 

## 1. Objetivo

O objetivo deste laboratorio foi implementar dois programas distribuidos em Python com `mpi4py`.

No primeiro exercicio, foi feita a multiplicacao de duas matrizes quadradas utilizando divisão de linhas entre os processos MPI. No segundo exercicio, foi utilizado o metodo de Monte Carlo para estimar o valor de pi a partir de pontos aleatorios gerados pelos processos.

## 2. Tecnologias utilizadas

- Python 3
- `mpi4py`
- NumPy (versoes sequencial e multithreaded)
- OpenMPI
- Docker
- Docker Compose
- Ubuntu 22.04

## 3. Configuracao do cluster

O cluster foi montado com quatro containers Docker:

- `master`
- `worker1`
- `worker2`
- `worker3`

Cada container recebeu Python, OpenMPI, `mpi4py` e SSH. O master conseguiu acessar os tres workers por SSH e o arquivo `hosts` foi usado pelo `mpirun` para iniciar quatro processos, um em cada no.

Comandos utilizados para iniciar e testar o cluster:

```powershell
docker compose up -d --build
docker compose exec master su - mpiuser -c "ssh worker1 hostname"
docker compose exec master su - mpiuser -c "ssh worker2 hostname"
docker compose exec master su - mpiuser -c "ssh worker3 hostname"
docker compose exec master su - mpiuser -c "mpirun --hostfile hosts -np 4 hostname"
```

Saida observada no teste de hosts:

```text
master
worker2
worker3
worker1
```

## 4. Exercicio 1 - Multiplicacao de matrizes distribuidas

No processo `rank 0`, foram geradas as matrizes A e B. As duas matrizes foram enviadas para todos os processos com `comm.bcast`.

Cada processo calculou apenas uma parte das linhas da matriz C. Depois, as partes calculadas foram reunidas no processo 0 com `comm.gather`. Foram executados testes com matrizes de tamanho 300, 600 e 1000.

Tambem foram executadas versoes sequencial e com quatro threads locais para comparar os tempos.

Os tempos MPI registrados nas capturas foram exibidos em segundos pelo programa e convertidos para milissegundos na tabela.

| Dimensao | Tempo sequencial (ms) | Tempo com threads (ms) | Tempo MPI (ms) |
|----------|-----------------------:|-----------------------:|---------------:|
| 300      | 77,19                  | 219,74                 | 1.850,00       |
| 600      | 8,05                   | 136,77                 | 15.490,00      |
| 1000     | 22,16                  | 135.19                 | 71.900,00      |

As execucoes do MPI produziram, nas capturas, aproximadamente `1,85 s` para `N = 300`, `15,49 s` para `N = 600` e `71,90 s` para `N = 1000`. Como o programa exibiu a matriz completa, as saidas ficaram muito longas.

O print da versao multithreaded fornecido registra os tempos de `219,74 ms` para `N = 300` e `136,77 ms` para `N = 600`. O tempo correspondente a `N = 1000` nao aparece na captura consultada e, por isso, nao foi preenchido nesta tabela.

Na versao utilizada, a verificacao do resultado foi feita pela matriz `C` reunida no processo `rank 0`, e nao por checksum.

Saida observada no teste com N = 1000:

```text
Processo 0 de 4
Processo 1 de 4
Processo 2 de 4
Processo 3 de 4
Tempo MPI: 71.90 s
```

## 5. Exercicio 2 - Estimativa de pi com Monte Carlo

No segundo exercicio, cada processo gerou uma parte dos 10.000.000 de pontos aleatorios. Quando um ponto ficou dentro do quarto de circulo, o processo incrementou seu contador local.

No final, os contadores foram somados no processo 0 usando `comm.reduce` com `MPI.SUM`. O valor de pi foi calculado com a formula:

```text
pi = 4 * pontos_dentro / total_de_pontos
```

Resultado obtido:

| Pontos | Tempo sequencial (ms) | Tempo com threads (ms) | Tempo MPI (ms) | Pi estimado |
|--------|-----------------------:|-----------------------:|---------------:|------------:|
| 10.000.000 | nao registrado | nao registrado | 759,67 | 3,141708 |

Saida observada no terminal:

```text
Pontos: 10000000; processos MPI: 4
Pontos internos acumulados: 7854270
PI aproximado: 3.141708
Tempo distribuido MPI: 759.67 ms
```

O valor encontrado ficou proximo de pi. Como o metodo usa numeros aleatorios, pequenas variacoes no resultado sao esperadas.

## 6. Analise dos resultados

Nos testes de multiplicacao de matrizes, a versao MPI ficou mais lenta que as versoes locais. Isso aconteceu porque os quatro containers estavam executando no mesmo computador e houve custo para iniciar processos, enviar as matrizes e juntar os resultados.

No tamanho 1000, a versao com threads foi a mais rapida. As versoes sequencial e multithreaded utilizaram NumPy, enquanto a versao MPI utilizou listas Python e comunicação por objetos com `mpi4py`. Essa diferenca de implementacao deve ser considerada ao comparar os tempos.

No Monte Carlo, a versao MPI foi mais rapida que a sequencial e a com threads. Cada processo calculou uma parte dos pontos e, no final, foi necessario somente somar os contadores locais. Nesse caso, a quantidade de dados trocada entre os processos foi pequena.

## 7. Dificuldades encontradas

Durante a execução, o Docker Desktop estava parado e precisou ser iniciado antes de criar o cluster. Tambem foi necessario configurar SSH nos containers para que o master conseguisse iniciar processos nos workers com o `mpirun`.

Na primeira versao da multiplicacao de matrizes, o particionamento das linhas e a medicao de tempo precisaram ser corrigidos. Tambem foi necessario lidar com o grande volume de texto gerado pela impressao da matriz completa.

## 8. Conclusao

O laboratorio mostrou o uso de comunicação coletiva em MPI na pratica. Na multiplicacao de matrizes, foram usadas as operacoes `bcast` e `gather`. No metodo de Monte Carlo, foi usada a operacao `reduce` para somar os resultados de todos os processos.

Os testes tambem mostraram que MPI não é sempre mais rapido. Para tarefas pequenas ou para containers no mesmo computador, o custo da comunicação
 pode ser maior que o ganho do processamento distribuido. Para o Monte Carlo, a divisão de trabalho entre processos apresentou um resultado melhor porque cada processo precisou enviar apenas um contador ao final da execução.

## 9. Uso de inteligencia artificial

Foi utilizado o IA para esclarecer a sintaxe do `mpi4py` e revisar a organização deste relatorio. Exemplos de prompts utilizados foram: "explique o motivo do erro x ao usar o MPI neste código", "Ajude-me a organizar melhor os resultados nesse laboratório".

A execução dos programas, a coleta dos tempos, a conferencia das capturas e a analise dos resultados foram realizadas no ambiente do laboratorio. As sugestões da IA foram conferidas contra o codigo e contra a saida real do terminal.



## 10. Print das execuções no meu terminal

***Docker Build***
![Build e subida dos containers Docker](image.png)

***Listagem dos conteiners***
![Containers Docker em execução](image-1.png)

***Testes da comuncação ssh***
![Testes de comunicação SSH entre os containers](image-2.png)

***Teste inicial do exercicio 1 --> N=4***

Observação: O output ficou muito longo pois mostro a matriz final no terminal

![execução MPI inicial com N igual a 4](image-3.png)


***Executando o exercicio 1 --> N=300***

![execução MPI com N igual a 300](image-4.png)


***Executando o exercicio 1 --> N=600***

![execução MPI com N igual a 600](image-6.png)


***Executando o exercicio 1 --> N=1000***

![execução MPI com N igual a 1000](image-7.png)

***Executando exercício 2***

![execução do exercicio 2](image-8.png)


***Execuando código sequencial***

![alt text](image-9.png)

***Execuando código paralelo***

![alt text](image-10.png)