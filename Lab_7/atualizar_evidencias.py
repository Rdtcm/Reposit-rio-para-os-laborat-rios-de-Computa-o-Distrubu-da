"""Insere uma rodada coletada na seção 4, preservando as demais seções."""
from pathlib import Path
import json
import sys

BASE = Path(__file__).resolve().parent
folder = Path(sys.argv[1]).resolve()
data = json.loads((folder/'registros.json').read_text(encoding='utf-8'))
records = data['registros']
assert records[-1]['nome'] == 'logs-servidor', 'Coleta incompleta'
assert all(r['codigo_saida'] == r['esperado'] for r in records)
relative = folder.relative_to(BASE).as_posix()
def blocks(names):
    parts = []
    for r in records:
        if r['nome'] in names:
            # O TXT original mantém inclusive o form feed emitido por pdftotext.
            output = r['saida'].replace('\f', '\\f')
            parts.append(f"#### {r['nome']}\n\n```text\n$ {r['comando']}\n{output}\n[codigo de saida: {r['codigo_saida']}]\n```\n")
    return '\n'.join(parts)
section = f'''## 4. Execução e Evidências

### 4.1 Origem dos registros e inicialização

Executei novamente os códigos e registrei a saída completa de cada comando, incluindo stdout, stderr e código de saída. A coleta começou em {data['inicio_utc']}. Substituí os prints pelas transcrições integrais do terminal. Os blocos abaixo não omitem linhas; as quebras de linhas longas no PDF servem somente à diagramação. O caractere de controle de fim de página do TXT aparece como \\f para ficar visível.

Os arquivos originais de cada comando, o índice registros.json e terminal-completo.txt estão em {relative}/. O log desta rodada contém todas as linhas do servidor desde o início da coleta. O arquivo evidencias/server.log continua acumulando também as rodadas anteriores. O servidor é contínuo: os comandos de inicialização e consulta de logs registram sua execução sem encerrar o processo.

Todos os comandos abaixo foram executados na pasta Lab_7. Os casos de erro esperados retornaram código 1; os demais retornaram 0.

{blocks(['servidor','containers','health'])}
### 4.2 Entrega 1 - Compressão e verificação dos PDFs

O PDF com imagem passou de 729159 para 585050 bytes. O PDF somente com texto passou de 1441 para 2833 bytes. A leitura dos resultados confirmou uma página e a preservação do texto nos dois casos.

{blocks(['compressao-entrada','compressao-texto','verificacao-pdfs'])}
### 4.3 Entrega 2 - Extração e leitura completa do texto

Executei ConvertToTXT sobre os dois PDFs e li integralmente os arquivos produzidos. Os bytes e o conteúdo aparecem nas saídas abaixo.

{blocks(['extracao-entrada','conteudo-entrada','extracao-texto','conteudo-texto'])}
### 4.4 Entrega 2 - Conversão de formatos

Executei as conversões para PNG, JPEG e WEBP. A inspeção leu o formato real e as dimensões dos arquivos, confirmando 1200x900 nos três resultados.

{blocks(['conversao-png','conversao-jpg','conversao-webp','verificacao-formatos'])}
### 4.5 Entrega 2 - Redimensionamento

O caso 400x300 produziu essas dimensões. O limite 200x200 produziu 200x150, preservando a proporção da entrada.

{blocks(['redimensionamento-400x300','redimensionamento-200x200','verificacao-dimensoes'])}
### 4.6 Tratamento de erros pela linha de comando

Executei os casos de formato não permitido, arquivo ausente, PDF corrompido, PDF vazio e dimensão inválida. Cada execução retornou código 1. O arquivo ausente falhou localmente antes do envio de uma RPC.

{blocks(['erro-formato','erro-ausente','erro-pdf','erro-vazio','erro-dimensao'])}
### 4.7 Bateria completa de testes e concorrência

A saída integral abaixo registra os 22 testes aprovados, incluindo quatro chamadas simultâneas, validação do protocolo, limite de upload e preservação do arquivo de saída após erro. Não foram realizados testes de carga prolongada, cancelamento em andamento ou exaustão de recursos.

{blocks(['testes-completos'])}
### 4.8 Limpeza e log completo do servidor nesta coleta

A consulta dos diretórios temporários terminou com código 0 e sem linhas de resultado, indicando que não havia diretórios lab7-* naquele momento. A seguir, incluí toda a saída do log do servidor desde o início desta coleta, sem selecionar apenas as últimas linhas.

{blocks(['temporarios','logs-servidor'])}
'''
path = BASE/'relatorio.md'
text = path.read_text(encoding='utf-8-sig')
start, end = text.index('## 4. Execução e Evidências'), text.index('## 5. Análise dos Resultados')
text = text[:start] + section + text[end:]
text = text.replace('**Versão para preenchimento: testes executados; capturas de tela pendentes.**\n\n', '')
text = text.replace('| Captura de terminal bloqueada pelo controle do computador | Preservar logs e JSON reais; deixar os locais dos prints explicitamente pendentes |', '| Captura de terminal bloqueada pelo controle do computador | Registrar novas execuções e incluir as saídas completas no lugar dos prints |')
text = text.replace('As capturas de tela ainda precisam ser inseridas; esta versão não representa a entrega visual final nem substitui a demonstração em laboratório.', 'Registrei as saídas completas dos comandos e do servidor no lugar dos prints. Essas evidências documentam a execução realizada e não substituem a demonstração em laboratório.')
assert 'INSERIR PRINT' not in text
path.write_text(text, encoding='utf-8')
print('Relatório atualizado com', len(records), 'comandos completos:', relative)
