# Logging de aplicação e auditoria

O Flask usa `logging` com console e arquivo `/dados/app.log`, em UTC. As mensagens INFO registram requisição, tentativa de lock, concessão ou conflito, verificação no banco, gravação e liberação. Falhas de comunicação ou persistência produzem ERROR com traceback para diagnóstico. O JSON de auditoria é emitido em WARNING, conforme permitido no enunciado, com `level: AUDIT` no documento.

## Esquema de auditoria

Exemplo ilustrativo:

```json
{
  "timestamp_utc": "2026-10-24T18:00:05.123Z",
  "level": "AUDIT",
  "event_type": "AGENDAMENTO_CRIADO",
  "service": "servico-agendamento",
  "details": {
    "agendamento_id": 123,
    "cientista_id": 1,
    "telescopio_id": 1,
    "horario_inicio_utc": "2026-12-01T03:00:00.000Z",
    "horario_fim_utc": "2026-12-01T03:05:00.000Z",
    "timestamp_cliente_utc": "2026-10-24T18:00:05.000Z"
  }
}
```

Eventos permitidos: `AGENDAMENTO_CRIADO` e `AGENDAMENTO_CANCELADO`. Uma transição persistida gera um evento. Repetição de cancelamento não duplica auditoria. Requisições rejeitadas têm logs de aplicação, mas não eventos de sucesso.

O evento de negócio também é gravado na tabela `auditoria`, na mesma transação da alteração. O app.log é uma projeção emitida após commit: se o processo cair nesse intervalo, o evento permanece no banco, mas pode não aparecer no arquivo. Não se afirma entrega exatamente uma vez entre banco e arquivo. A trilha não tem API de edição; proteção contra alteração administrativa exigiria armazenamento adicional e controle de acesso, fora deste exercício.

## Coordenador

Cada linha de console é JSON com `timestamp_utc`, `level`, `service`, `event` e `resource`. Eventos: pedido recebido, lock concedido, recurso em uso e lock liberado. Não são registrados tokens. O mapa em memória não é persistido, e o relógio do coordenador serve ao diagnóstico, não à ordenação global de eventos.

## Coleta

```powershell
docker compose logs -f servico-agendamento servico-coordenador
docker compose logs demonstracao-sem-lock
docker compose exec -T servico-agendamento cat /dados/app.log
```

`node testes.mjs todos` salva respostas, extratos do banco, app.log de cada cenário e logs agregados em `evidencias/`. Os extratos permitem correlacionar o ID, o horário e o tipo do evento com a resposta HTTP. A pausa das demonstrações é declarada para que os logs não sejam interpretados como medição de desempenho da aplicação padrão.
