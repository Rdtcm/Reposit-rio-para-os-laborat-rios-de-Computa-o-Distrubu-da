"""Preenche somente os blocos automáticos do relatório com medições reais."""

from collections import defaultdict
import csv
import io
import json
from pathlib import Path
import statistics


def substituir(texto, nome, conteudo):
    inicio, fim = f'<!-- AUTO:{nome}:INICIO -->', f'<!-- AUTO:{nome}:FIM -->'
    if texto.count(inicio) != 1 or texto.count(fim) != 1:
        raise ValueError(f'Marcadores ausentes ou duplicados: {nome}')
    antes, resto = texto.split(inicio)
    _, depois = resto.split(fim)
    return antes + inicio + '\n\n' + conteudo + '\n\n' + fim + depois


def main():
    pasta = Path(__file__).resolve().parent
    resultados = pasta / 'resultados'
    manifesto = resultados / 'manifesto.json'
    if not manifesto.exists():
        raise SystemExit('Execute primeiro executar_experimentos.py até o final.')
    grupos = defaultdict(list)
    for nome in json.loads(manifesto.read_text(encoding='utf-8')):
        r = json.loads((resultados / nome).read_text(encoding='utf-8'))
        if r['verificacao_serial'] is not True:
            raise ValueError(f'Resultado sem validação serial: {nome}')
        p = r['parametros']
        grupos[(p['linhas'], p['colunas'], r['processos'], p['atraso'])].append(r)
    medianas = {k: statistics.median(r['tempo_ms'] for r in rs) for k, rs in grupos.items()}
    tabela = ['| Imagem | Processos | Atraso (s × rank ímpar) | Repetições | Mediana (ms) | Mín.–máx. (ms) | Speedup | Eficiência |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer, lineterminator='\n')
    writer.writerow(['linhas', 'colunas', 'processos', 'atraso', 'repeticoes', 'mediana_ms', 'min_ms', 'max_ms', 'speedup', 'eficiencia'])
    for k, rs in sorted(grupos.items()):
        linhas, colunas, processos, atraso = k
        tempos = [r['tempo_ms'] for r in rs]
        base = medianas.get((linhas, colunas, 1, atraso))
        speedup = base / medianas[k] if base else None
        eficiencia = speedup / processos if speedup else None
        s = f'{speedup:.3f}' if speedup else 'não se aplica'
        e = f'{100*eficiencia:.2f}%' if eficiencia else 'não se aplica'
        tabela.append(f'| {linhas} × {colunas} | {processos} | {atraso:g} | {len(rs)} | {medianas[k]:.3f} | '
                      f'{min(tempos):.3f}–{max(tempos):.3f} | {s} | {e} |')
        writer.writerow([*k, len(rs), medianas[k], min(tempos), max(tempos), speedup, eficiencia])
    observacoes = []
    for n in sorted({k[0] for k in grupos if k[0] == k[1]}):
        for processos in (2, 4, 8):
            sem = medianas[(n, n, processos, 0.0)]
            com = medianas[(n, n, processos, 0.5)]
            base = medianas[(n, n, 1, 0.0)]
            comparacao = 'menor' if sem < base else 'maior ou igual'
            observacoes.append(f'- **{n} × {n}, {processos} processos:** sem pausa, {sem:.3f} ms, tempo {comparacao} '
                               f'ao de 1 processo ({base:.3f} ms). Com pausa, {com:.3f} ms; '
                               f'diferença observada de {com-sem:.3f} ms. Speedup sem pausa: {base/sem:.3f}.')
    auditoria = []
    for k, rs in sorted(grupos.items()):
        if k[3] != 0.5 or k[2] != 4:
            continue
        r = rs[0]
        g = r['metricas']
        auditoria.append(f"**{k[0]} × {k[1]}, 4 processos, primeira repetição:** {g['pixels']} pixels, "
                         f"{g['suspeitos']} suspeitos, {g['altos']} altos; esquerdo {g['esquerdo']}, direito {g['direito']}. "
                         f"Diagnóstico: {r['diagnostico']}. Maior contagem: {r['lateralidade']}.")
        auditoria.extend(f"- Rank {l['rank']} ({l['host']}), linhas [{l['inicio']},{l['fim_exclusivo']}): "
                         f"{l['pixels']} pixels, {l['suspeitos']} suspeitos, {l['classificacao']}; "
                         f"espera na barreira: {l['barreira_ms']:.3f} ms."
                         for l in r['relatos'])
        auditoria.append('')
    relatorio = pasta / 'relatorio.md'
    texto = relatorio.read_text(encoding='utf-8')
    texto = substituir(texto, 'TABELA', '\n'.join(tabela))
    texto = substituir(texto, 'OBSERVACOES', '\n'.join(observacoes))
    texto = substituir(texto, 'AUDITORIA', '\n'.join(auditoria))
    ambiente = (resultados / 'ambiente.txt').read_text(encoding='utf-8')
    texto = substituir(texto, 'AMBIENTE', '```text\n' + ambiente.strip() + '\n```')
    relatorio.write_text(texto, encoding='utf-8')
    (resultados / 'resumo.csv').write_text(csv_buffer.getvalue(), encoding='utf-8-sig')


if __name__ == '__main__':
    main()
