"""Laboratório 4: as 12 etapas do guia, com dados sintéticos reproduzíveis."""

import argparse
import json
from pathlib import Path
import socket
import time

import numpy as np


def argumentos():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--linhas', type=int, default=2000)
    parser.add_argument('--colunas', type=int, default=2000)
    parser.add_argument('--limiar-suspeito', type=int, default=200)
    parser.add_argument('--limiar-alto', type=int, default=230)
    parser.add_argument('--pct-critico', type=float, default=5.0)
    parser.add_argument('--pct-altos', type=float, default=1.0,
                        help='Presença expressiva: percentual de pixels > limiar-alto.')
    parser.add_argument('--atraso', type=float, default=0.5,
                        help='Pausa em segundos multiplicada pelo rank ímpar; 0 desativa.')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--foco', choices=['direito', 'esquerdo', 'nenhum'], default='direito')
    parser.add_argument('--saida', type=Path, help='Salvar métricas e auditoria em JSON.')
    parser.add_argument('--verificar', action='store_true', help='Comparar com análise serial fora do tempo medido.')
    args = parser.parse_args()
    if args.linhas < 1 or args.colunas < 2:
        parser.error('Use pelo menos 1 linha e 2 colunas.')
    if not 0 <= args.limiar_suspeito < args.limiar_alto <= 255:
        parser.error('Exige-se 0 <= limiar-suspeito < limiar-alto <= 255.')
    if not 1 <= args.pct_critico <= 100 or not 0 < args.pct_altos <= 100:
        parser.error('pct-critico deve estar em [1,100] e pct-altos em (0,100].')
    if not np.isfinite(args.atraso) or args.atraso < 0 or args.seed < 0:
        parser.error('Atraso deve ser finito e não negativo; seed deve ser não negativa.')
    return args


def gerar_imagem(p):
    """Fundo suave, campos elípticos e um foco proporcional ao tamanho da imagem."""
    rng = np.random.default_rng(p['seed'])
    linhas, colunas = p['linhas'], p['colunas']
    y = np.linspace(-1, 1, linhas, dtype=np.float32)[:, None]
    x = np.linspace(-1, 1, colunas, dtype=np.float32)[None, :]
    imagem = rng.integers(25, 50, (linhas, colunas), dtype=np.uint8)
    gradiente = (12 * (1 - np.abs(y))).astype(np.uint8)
    imagem += gradiente
    for centro in (-0.45, 0.45):
        campo = ((x - centro) / 0.34) ** 2 + (y / 0.85) ** 2 <= 1
        imagem[campo] += 30
    if p['foco'] != 'nenhum':
        inicio, fim = int(0.30 * linhas), max(int(0.45 * linhas), int(0.30 * linhas) + 1)
        meio = colunas // 2
        base, largura = (meio, colunas - meio) if p['foco'] == 'direito' else (0, meio)
        c0 = base + int(0.20 * largura)
        c1 = min(base + largura, max(c0 + 1, base + int(0.60 * largura)))
        imagem[inicio:fim, c0:c1] = rng.integers(180, 245, (fim - inicio, c1 - c0), dtype=np.uint8)
    return imagem


def intervalos(linhas, size):
    """Distribui o resto nas primeiras faixas, sem padding ou perda de pixels."""
    quociente, resto = divmod(linhas, size)
    inicio = 0
    resultado = []
    for rank in range(size):
        fim = inicio + quociente + (rank < resto)
        resultado.append((inicio, fim))
        inicio = fim
    return resultado


def classificar(total, suspeitos, altos, p):
    if total == 0:
        return 'SEM DADOS'
    if 100 * suspeitos / total >= p['pct_critico'] or 100 * altos / total >= p['pct_altos']:
        return 'CRÍTICA'
    return 'ATENÇÃO' if 100 * suspeitos / total >= 1 else 'NORMAL'


def analisar(bloco, p):
    meio = p['colunas'] // 2
    suspeitos = bloco > p['limiar_suspeito']
    return {
        'pixels': int(bloco.size),
        'soma': int(np.sum(bloco, dtype=np.uint64)),
        'maximo': int(bloco.max()) if bloco.size else 0,
        'suspeitos': int(np.count_nonzero(suspeitos)),
        'altos': int(np.count_nonzero(bloco > p['limiar_alto'])),
        'esquerdo': int(np.count_nonzero(suspeitos[:, :meio])),
        'direito': int(np.count_nonzero(suspeitos[:, meio:])),
    }


def main():
    # Etapa 1. Importação local permite testar a lógica sem instalar MPI no Windows.
    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank, size = comm.Get_rank(), comm.Get_size()
    args = argumentos()
    inicio_total = MPI.Wtime()
    imagem = None
    parametros = None
    # Etapas 2 e 3: somente o root cria a imagem e define a configuração global.
    if rank == 0:
        parametros = {k: v for k, v in vars(args).items() if k not in ('saida', 'verificar')}
        imagem = gerar_imagem(parametros)
    p = comm.bcast(parametros, root=0)
    # Etapas 4 e 5: faixas balanceadas, inclusive quando size > linhas.
    comm.Barrier()
    faixas = intervalos(p['linhas'], size)
    blocos = [imagem[a:b, :] for a, b in faixas] if rank == 0 else None
    bloco = comm.scatter(blocos, root=0)
    # Etapas 6 e 7: operações vetorizadas examinam todos os pixels locais.
    inicio_analise = MPI.Wtime()
    local = analisar(bloco, p)
    local['classificacao'] = classificar(local['pixels'], local['suspeitos'], local['altos'], p)
    local['analise_ms'] = (MPI.Wtime() - inicio_analise) * 1000
    # Etapas 8 e 9: mede a espera em cada processo sem comparar relógios de hosts.
    pausa = p['atraso'] * rank if rank % 2 else 0
    time.sleep(pausa)
    inicio_barreira = MPI.Wtime()
    comm.Barrier()
    local['barreira_ms'] = (MPI.Wtime() - inicio_barreira) * 1000
    local.update(rank=rank, host=socket.gethostname(), inicio=faixas[rank][0],
                 fim_exclusivo=faixas[rank][1], pausa_s=pausa)
    # Etapa 10: seis somas e um máximo, sem substituir reduce por gather.
    global_ = {}
    for chave in ('pixels', 'soma', 'suspeitos', 'altos', 'esquerdo', 'direito', 'maximo'):
        global_[chave] = comm.reduce(local[chave], op=MPI.MAX if chave == 'maximo' else MPI.SUM, root=0)
    # Etapa 11: preserva a identidade e as métricas de cada faixa.
    relatos = comm.gather(local, root=0)
    if rank != 0:
        return
    tempo_ms = (MPI.Wtime() - inicio_total) * 1000
    verificacao = None
    if args.verificar:
        verificacao = analisar(imagem, p) == global_
        if not verificacao:
            raise RuntimeError('Métricas distribuídas divergiram da referência serial.')
    # Etapa 12. O tempo inclui geração, comunicação, análise, pausas e sincronização;
    # exclui inicialização do mpirun, impressão, verificação serial e escrita em disco.
    classe = classificar(global_['pixels'], global_['suspeitos'], global_['altos'], p)
    diagnostico = {'NORMAL': 'Sem Indícios Relevantes', 'ATENÇÃO': 'Atenção Clínica',
                   'CRÍTICA': 'Quadro Crítico / Alta Concentração de Alterações'}[classe]
    lado = ('Direito' if global_['direito'] > global_['esquerdo'] else
            'Esquerdo' if global_['esquerdo'] > global_['direito'] else 'Equilibrado')
    resultado = dict(parametros=p, processos=size, tempo_ms=tempo_ms, metricas=global_,
                     relatos=relatos, diagnostico=diagnostico, lateralidade=lado,
                     verificacao_serial=verificacao)
    print('\n' + '=' * 90)
    print('RELATÓRIO CONSOLIDADO DE TRIAGEM DISTRIBUÍDA - SIMULAÇÃO DIDÁTICA')
    print(f"Dimensões: {p['linhas']} x {p['colunas']} | Processos: {size} | Seed: {p['seed']}")
    print(f"Limiares: > {p['limiar_suspeito']} / > {p['limiar_alto']} | "
          f"Crítico: {p['pct_critico']}% suspeitos OU {p['pct_altos']}% altos")
    print(f"Tempo total: {tempo_ms:.3f} ms | Atraso por rank ímpar: {p['atraso']} s x rank")
    print(f"Pixels: {global_['pixels']} | Média: {global_['soma']/global_['pixels']:.4f} | Máximo: {global_['maximo']}")
    print(f"Suspeitos: {global_['suspeitos']} ({100*global_['suspeitos']/global_['pixels']:.4f}%) | Altos: {global_['altos']}")
    print(f"Esquerdo: {global_['esquerdo']} | Direito: {global_['direito']} | Maior contagem: {lado}")
    print(f'Diagnóstico simulado: {diagnostico}')
    print('--- Auditoria: intervalos de linhas [início, fim), índices a partir de zero ---')
    for r in relatos:
        print(f"Rank {r['rank']:02d} @ {r['host']} | [{r['inicio']},{r['fim_exclusivo']}) | "
              f"Pixels {r['pixels']} | Suspeitos {r['suspeitos']} | Altos {r['altos']} | "
              f"Máx {r['maximo']} | {r['classificacao']}")
        print(f"  Análise {r['analise_ms']:.3f} ms | Pausa {r['pausa_s']:.1f} s | Espera barreira {r['barreira_ms']:.3f} ms")
    if args.verificar:
        print('Verificação contra referência serial: OK (fora do tempo medido)')
    print('=' * 90, flush=True)
    if args.saida:
        args.saida.parent.mkdir(parents=True, exist_ok=True)
        args.saida.write_text(json.dumps(resultado, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
