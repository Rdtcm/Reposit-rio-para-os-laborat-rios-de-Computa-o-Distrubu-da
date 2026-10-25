# Contrato REST do SCTEC

Base local: `http://localhost:5000`. JSON UTF-8. Erros: `{"error":"descrição"}`. Não há autenticação; a aplicação é uma demonstração local. Datas de entrada exigem ISO 8601 com fuso e são convertidas para UTC.

## Recursos principais

| Método | Caminho | Resposta |
|---|---|---|
| GET | / | 200: interface HTML |
| GET | /health | 200: estado do banco e opção lock_enabled |
| GET | /time | 200: timestamp_utc e unix_ms; Cache-Control: no-store |
| GET | /cientistas | 200: items e links self/criar |
| POST | /cientistas | 201: cadastro criado; 400: nome inválido |
| GET | /telescopios | 200: items e link self |
| GET | /agendamentos | 200: items e links self/criar/time |
| POST | /agendamentos | 201: recurso, HATEOAS e cabeçalho Location |
| GET | /agendamentos/{id} | 200: recurso; 404: não encontrado |
| DELETE | /agendamentos/{id} | 200: recurso cancelado; 404: não encontrado |

`GET /agendamentos?inicio=<ISO-8601>` filtra por início normalizado em UTC. Cancelados continuam na listagem para preservar histórico.

### Cadastro de cientista

Corpo de POST /cientistas:

```json
{"nome":"Cientista de exemplo"}
```

### Criação de agendamento

Exemplo de entrada (valores ilustrativos, não evidência):

```json
{
  "cientista_id": 1,
  "telescopio_id": 1,
  "horario_inicio_utc": "2026-12-01T03:00:00Z",
  "horario_fim_utc": "2026-12-01T03:05:00Z",
  "timestamp_cliente_utc": "2026-10-24T18:00:00Z"
}
```

Resposta 201 contém todos os campos de Agendamento definidos em MODELOS.md e:

```json
{
  "_links": {
    "self": {"href":"/agendamentos/123","method":"GET"},
    "collection": {"href":"/agendamentos","method":"GET"},
    "cancelar": {"href":"/agendamentos/123","method":"DELETE"}
  }
}
```

Erros de criação: 400 para dados inválidos, datas sem fuso, intervalo invertido ou entidades inexistentes; 409 para recurso ocupado ou horário conflitante; 503 para indisponibilidade do coordenador ou falha de banco. JSON malformado retorna 400; tipo de conteúdo inadequado, 415; corpo maior que 16 KiB, 413. Nenhuma reserva é criada quando não é possível obter o lock.

### Cancelamento e HATEOAS

O cliente deve ler `_links.cancelar.href` e `_links.cancelar.method`, sem construir a URL de cancelamento. A resposta 200 muda `status` para `cancelado` e passa a conter apenas `self` e `collection`. Repetir DELETE mantém 200 e não gera outro evento de cancelamento. Um intervalo cancelado fica disponível para nova reserva. Disputa pelo lock retorna 409; falha de infraestrutura retorna 503.

### Tempo

`GET /time` fornece um instante UTC e seu equivalente em milissegundos desde Unix epoch. O cliente faz cinco amostras e usa a de menor RTT: tempo estimado na recepção = tempo do servidor + RTT/2. O avanço usa `performance.now()`, sem modificar o relógio do sistema operacional. A compensação presume atrasos aproximadamente simétricos; não garante ordem absoluta dos cliques ou ausência de erro.

## Coordenador

Base local de diagnóstico: `http://localhost:3000`. Entre containers: `http://servico-coordenador:3000`.

| Método | Caminho | Corpo | Resposta |
|---|---|---|---|
| GET | /health | nenhum | 200: status ok |
| POST | /lock | resource: string de 1 a 200 caracteres | 200: resource e token; 409: ocupado; 400: inválido |
| POST | /unlock | resource e token: strings | 200: released true; 409: token incorreto ou lock ausente; 400: inválido |

O token só aparece na comunicação com o coordenador, não no JSON público do agendamento nem nos logs de aplicação. A exclusão é centralizada em uma única instância Node; não executar múltiplas réplicas desse mapa em memória como se compartilhassem o mesmo estado.
