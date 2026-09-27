"""Execute dentro do master: python3 executar_experimentos.py --repeticoes 3."""

import argparse
import json
from pathlib import Path
import platform
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeticoes', type=int, default=3)
    parser.add_argument('--incluir-6000', action='store_true')
    args = parser.parse_args()
    if args.repeticoes < 1:
        parser.error('Use pelo menos uma repetição.')
    pasta = Path(__file__).resolve().parent
    resultados = pasta / 'resultados'
    resultados.mkdir(exist_ok=True)
    # O manifesto identifica exclusivamente os arquivos desta bateria.
    # Só é substituído após todos os experimentos terminarem com sucesso.
    ambiente = [f'Python: {sys.version}', f'Plataforma: {platform.platform()}']
    for cmd in (['mpirun', '--version'], ['python3', '-c',
                'import numpy, mpi4py; print("NumPy:", numpy.__version__); print("mpi4py:", mpi4py.__version__)'],
                ['lscpu'], ['cat', '/sys/fs/cgroup/cpu.max'], ['cat', '/sys/fs/cgroup/memory.max']):
        r = subprocess.run(cmd, text=True, capture_output=True)
        ambiente.append('$ ' + ' '.join(cmd) + '\n' + r.stdout + r.stderr)
    for host in ('master', 'worker1', 'worker2', 'worker3'):
        r = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', host,
                            'hostname; nproc; python3 -c "import numpy, mpi4py; print(numpy.__version__, mpi4py.__version__)"'],
                           text=True, capture_output=True)
        ambiente.append(f'$ ssh {host} ...\n{r.stdout}{r.stderr}')
        if r.returncode:
            raise SystemExit(f'Falha de SSH/dependências em {host}: {r.stderr}')
    (resultados / 'ambiente.txt').write_text('\n\n'.join(ambiente), encoding='utf-8')
    tamanhos = [500, 2000, 4000] + ([6000] if args.incluir_6000 else [])
    casos = [(n, n, processos, atraso) for n in tamanhos
             for processos in (1, 2, 4, 8) for atraso in (0.0, 0.5)]
    casos.append((2003, 2000, 4, 0.5))
    arquivos = []
    for linhas, colunas, processos, atraso in casos:
        for repeticao in range(1, args.repeticoes + 1):
            nome = f'{linhas}x{colunas}_p{processos}_a{atraso}_r{repeticao}'
            cmd = ['mpirun', '--hostfile', '/home/mpiuser/hosts', '--oversubscribe',
                   '--map-by', 'node', '--bind-to', 'none', '-np', str(processos),
                   'python3', str(pasta / 'processamento_imagens.py'),
                   '--linhas', str(linhas), '--colunas', str(colunas),
                   '--atraso', str(atraso), '--verificar', '--saida', str(resultados / f'{nome}.json')]
            print(f'\n>>> {nome}\n$ {" ".join(cmd)}', flush=True)
            with (resultados / f'{nome}.txt').open('w', encoding='utf-8') as log:
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, encoding='utf-8', cwd=pasta)
                for linha in proc.stdout:
                    print(linha, end='', flush=True)
                    log.write(linha)
                if proc.wait():
                    raise SystemExit(f'Falha no caso {nome}. Consulte o log.')
            arquivos.append(f'{nome}.json')
    (resultados / 'manifesto.json').write_text(json.dumps(arquivos, indent=2), encoding='utf-8')
    subprocess.run(['python3', str(pasta / 'atualizar_relatorio.py')], check=True, cwd=pasta)
    print('\nBateria concluída. Tabelas e observações reais inseridas em relatorio.md.')


if __name__ == '__main__':
    main()
