# Modelos do SCTEC

## Cientista

| Campo | Tipo | Regra |
|---|---|---|
| id | inteiro | Chave primária positiva |
| nome | texto | Obrigatório; 1 a 120 caracteres após remoção de espaços externos |

O cadastro inicial contém o cientista de demonstração com ID 1. Não há autenticação nesta atividade: o ID identifica o cadastro, mas não comprova a identidade do solicitante.

## Telescópio

| Campo | Tipo | Regra |
|---|---|---|
| id | inteiro | Chave primária positiva |
| nome | texto | Obrigatório |

O telescópio inicial é Hubble-Acad, ID 1. O catálogo é consultável e não possui rota de alteração no escopo deste laboratório.

## Agendamento

| Campo | Tipo | Regra |
|---|---|---|
| id | inteiro | Chave primária gerada pelo banco |
| cientista_id | inteiro | Chave estrangeira para cientista existente |
| telescopio_id | inteiro | Chave estrangeira para telescópio existente |
| horario_inicio_utc | texto ISO 8601 | Entrada com fuso; normalização para UTC com milissegundos |
| horario_fim_utc | texto ISO 8601 | Estritamente posterior ao início |
| timestamp_cliente_utc | texto ISO 8601 | Instante informado pelo cliente sincronizado; não determina prioridade |
| criado_em_utc | texto ISO 8601 | Instante autoritativo gerado pelo servidor |
| status | texto | ativo ou cancelado |

Os intervalos são semiabertos: [início, fim). Há conflito quando `inicio_existente < fim_novo` e `fim_existente > inicio_novo`, no mesmo telescópio e com status ativo. Intervalos adjacentes são permitidos. O cancelamento preserva o registro e remove o link de ação `cancelar` da representação.

O lock utiliza `telescopio-{id}`, uma granularidade mais conservadora que a chave por horário ilustrada no enunciado: protege também sobreposições com inícios diferentes. A operação inclui verificação e escrita na mesma transação `BEGIN IMMEDIATE`. Isso serializa escritas no SQLite e preserva a consistência mesmo se o coordenador reiniciar durante uma operação. O custo é menor concorrência entre intervalos independentes.

## Auditoria

| Campo | Tipo | Regra |
|---|---|---|
| id | inteiro | Chave primária |
| documento | texto JSON | Evento com timestamp, nível, tipo, serviço e detalhes |

O evento é inserido na mesma transação da reserva ou do cancelamento. A API não fornece rotas de atualização ou exclusão da auditoria. Isso não equivale a armazenamento inviolável: um administrador com acesso ao volume pode alterar o banco ou o log.

## Lock efêmero

Mapa em memória no coordenador: `resource -> token UUID`. Aquisição é imediata: 200 se livre e 409 se ocupado, sem fila. A liberação exige o token proprietário. Não há expiração automática para evitar que uma operação lenta perca sua exclusão; falhas que impeçam o `finally` podem deixar locks órfãos. Reinício limpa esse estado. O banco e a auditoria persistem nos volumes Docker.

## Versão vulnerável da Entrega 2

O serviço `demonstracao-sem-lock` desabilita o coordenador e separa a leitura da escrita. A pausa de um segundo amplia a janela da corrida e permite observar duplicidades reais. Seu banco e sua porta são separados da aplicação padrão; essa configuração existe apenas para reproduzir a falha solicitada.
