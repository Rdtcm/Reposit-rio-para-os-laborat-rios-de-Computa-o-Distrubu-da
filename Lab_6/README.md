# Laboratório 6 - Web Services e Containers

Implementação das cinco entregas do SCTEC descritas em `webservices.pdf`.

## Executar

Requisitos: Docker Desktop em execução e Docker Compose. Node.js 18+ no host apenas para rodar `testes.mjs` (usa fetch nativo; sem npm install no host).

```powershell
cd Lab_6
docker compose up -d --build --wait
docker compose ps
```

Abra http://localhost:5000. O cliente sincroniza o relógio, permite criar reservas e oferece cancelamento pelos links HATEOAS recebidos da API. Horários do formulário são locais e enviados em UTC. Há um cientista e um telescópio iniciais para demonstração. API completa em [API.md](API.md).

## Experimentos das entregas 2 e 3

```powershell
docker compose --profile experimentos up -d --build --wait
node testes.mjs todos
```

O comando inicia a aplicação padrão (5000), o coordenador (3000), a demonstração vulnerável (5001) e a demonstração protegida (5002). Os bancos são separados. As duas demonstrações usam uma pausa explícita de um segundo entre a checagem e a escrita, para tornar a disputa visível. A aplicação padrão não usa essa pausa.

O teste completo faz requisições reais, consulta os bancos, salva logs e interrompe brevemente o coordenador do Lab 6 para verificar HTTP 503 e recuperação. Não execute a suíte durante uma apresentação em andamento. Cada execução usa horários novos e preserva registros anteriores. Os arquivos de evidência da suíte são atualizados; copie-os antes de repetir caso queira preservar uma rodada específica.

Casos individuais:

```powershell
node testes.mjs sem-lock
node testes.mjs com-lock
node testes.mjs padrao
node testes.mjs contratos
node testes.mjs relogio
node testes.mjs falha
```

`sem-lock` espera dez respostas 201 e dez reservas conflitantes. `com-lock` espera uma 201 e nove 409. A suíte também verifica entradas inválidas, sobreposição parcial, horários adjacentes, cancelamento idempotente, reserva após cancelamento, token proprietário e compensação de um cliente simulado dois segundos adiantado. Veja os resultados reais em `evidencias/testes-todos.json`.

## Logs e banco

```powershell
docker compose logs -f servico-agendamento servico-coordenador
docker compose logs demonstracao-sem-lock demonstracao-com-lock
docker compose exec -T servico-agendamento cat /dados/app.log
docker compose exec -T servico-agendamento python -c "import sqlite3; c=sqlite3.connect('/dados/agenda.db'); print(c.execute('SELECT id, horario_inicio_utc, status FROM agendamento').fetchall())"
```

Os volumes nomeados preservam banco e app.log. Para encerrar sem apagar dados:

```powershell
docker compose --profile experimentos down
```

## Arquivos por entrega

| Entrega | Arquivos |
|---|---|
| 1 - Projeto | MODELOS.md, API.md, LOGGING.md |
| 2 - Corrida | servico-agendamento/app.py, testes.mjs, perfil demonstracao-sem-lock |
| 3 - Coordenação | servico-coordenador/index.js, try/finally no Flask |
| 4 - Tempo e cliente | /time, static/index.html, static/cliente.js |
| 5 - Containers | Dockerfiles, docker-compose.yml, evidencias/compose.log |

## Limites do experimento

O timestamp sincronizado não é usado como fila de prioridade: vence quem adquire o lock, sem garantia FIFO. O relógio do Flask é a referência do exercício, sem validação NTP externa. O coordenador é único e mantém locks em memória; uma queda do detentor pode deixar lock órfão, exigindo intervenção. `BEGIN IMMEDIATE` protege a transação no SQLite, mas não torna o sistema altamente disponível. Não há autenticação ou trilha à prova de adulteração administrativa. As portas são publicadas somente em loopback.

## Relatório

Para executar cada entrega e inserir as capturas, siga [GUIA_PRINTS.md](GUIA_PRINTS.md). O Markdown contém espaços identificados para os prints; o PDF deve ser regenerado depois de preenchê-los.

`relatorio.md` é a fonte editável; o gerador lê esse arquivo sem sobrescrevê-lo. O PDF usa somente o layout de Lab_3/relatorio.pdf; fatos e resultados são do SCTEC. Comandos de geração e validação são descritos no arquivo `gerar_relatorio.py`.

```powershell
docker compose --profile ferramentas run --rm --build relatorio
```

O comando cria `relatorio.pdf` e imagens de revisão em `tmp/pdfs/`. Confira as páginas após editar o Markdown. A geração não modifica capturas nem a fonte editável. A interface não foi inspecionada em navegador nesta sessão; valide manualmente o formulário antes da apresentação.
