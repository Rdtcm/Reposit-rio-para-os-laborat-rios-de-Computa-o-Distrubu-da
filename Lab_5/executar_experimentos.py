"""Executa os dois servidores, testa HTTP real e registra as saídas observadas."""
import contextlib
from datetime import datetime
import io
import json
from pathlib import Path
import subprocess
import sys
import time

import requests

BASE = Path(__file__).resolve().parent
EVIDENCIAS = BASE / 'evidencias'


def executar():
    EVIDENCIAS.mkdir(exist_ok=True)
    registros = []
    processos = []
    logs = []
    for porta in (5000, 3000):
        import socket
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1', porta)) == 0:
                raise RuntimeError(f'Porta {porta} ocupada. Encerre o serviço antes da bateria.')
    try:
        for nome, comando in [('flask', [sys.executable, 'app.py']), ('node', ['node', 'index.js'])]:
            log = open(EVIDENCIAS / f'{nome}.log', 'w', encoding='utf-8')
            logs.append(log)
            processos.append(subprocess.Popen(comando, cwd=BASE, stdout=log, stderr=log))
        for porta in (5000, 3000):
            for tentativa in range(50):
                try:
                    if requests.get(f'http://localhost:{porta}/status', timeout=1).ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(.1)
            else:
                raise RuntimeError(f'Serviço {porta} não iniciou')

        def verificar(nome, metodo, porta, rota, codigo=200, **kwargs):
            resposta = requests.request(metodo, f'http://localhost:{porta}{rota}', timeout=7, **kwargs)
            dados = resposta.json()
            registros.append({'teste': nome, 'metodo': metodo, 'url': resposta.url,
                              'http': resposta.status_code, 'resposta': dados})
            assert resposta.status_code == codigo, registros[-1]
            return dados

        for porta in (5000, 3000):
            exemplo = verificar('Exemplo da aula', 'GET', porta, '/api/data')
            assert set(exemplo) == {'mensagem', 'status', 'tecnologia'}
        for id in ('1', '2'):
            fiscal = verificar('Exercício 1 - fiscal', 'GET', 5000, f'/detalhes/{id}')
            estoque = verificar('Exercício 1 - estoque', 'GET', 3000, f'/estoque/{id}')
            completo = verificar('Exercício 2 - proxy', 'GET', 3000, f'/api/full-info/{id}')
            assert completo == {'id': id, **estoque, **fiscal}
        for porta in (5000, 3000):
            dados = verificar('Exercício 3 - status', 'GET', porta, '/status')
            assert set(dados) == {'service', 'status', 'timestamp'} and dados['status'] == 'online'
            datetime.fromisoformat(dados['timestamp'].replace('Z', '+00:00'))
        produto = {'id': '3', 'nome': 'teclado', 'estoque': 20, 'preco_base': 200.0, 'categoria': 'Perifericos'}
        novo = verificar('Exercício 4 - cadastro distribuído', 'POST', 3000, '/cadastrar', 201, json=produto)
        assert novo == {'id': '3', 'nome': 'TECLADO', 'estoque': 20, 'preco': 240.0, 'categoria': 'Perifericos'}
        assert verificar('Exercício 4 - consulta fiscal', 'GET', 5000, '/detalhes/3')['preco'] == 240.0
        assert verificar('Exercício 4 - consulta comercial', 'GET', 3000, '/estoque/3')['nome'] == 'TECLADO'
        assert verificar('Exercício 4 - consulta integrada', 'GET', 3000, '/api/full-info/3') == novo
        verificar('Cadastro duplicado', 'POST', 3000, '/cadastrar', 409, json=produto)
        for porta, rota in [(5000, '/detalhes/'), (3000, '/estoque/'), (3000, '/api/full-info/')]:
            for id in ('-5', 'abc', '0', '1.5'):
                dados = verificar('Exercício 5 - ID inválido', 'GET', porta, rota + id, 400)
                assert dados == {'error': 'INVALID_ID', 'message': 'O ID deve ser um inteiro positivo'}
            verificar('Produto ausente', 'GET', porta, rota + '999', 404)
        for porta, rota in [(5000, '/fiscal/cadastrar'), (3000, '/cadastrar')]:
            verificar('Dados inválidos', 'POST', porta, rota, 400, json={**produto, 'id': '4', 'preco_base': -1})
            verificar('JSON malformado', 'POST', porta, rota, 400, data='{', headers={'Content-Type': 'application/json'})
        verificar('Cadastro fiscal direto', 'POST', 5000, '/fiscal/cadastrar', 201,
                  json={'id': '5', 'preco_base': 100.01, 'categoria': 'Teste'})
        assert verificar('Arredondamento monetário', 'GET', 5000, '/detalhes/5')['preco'] == 120.01
        saidas = []
        for argumentos, entrada in [([], '1\n'), (['--id', '2'], None), (['--id', '3'], None), (['--status'], None), (['--id', '-5'], None)]:
            comando = [sys.executable, 'cliente_relatorio.py', *argumentos]
            resultado = subprocess.run(comando, cwd=BASE, input=entrada, capture_output=True, text=True, encoding='utf-8', env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'})
            assert resultado.returncode == (1 if argumentos == ['--id', '-5'] else 0), resultado.stderr
            saidas.append('$ python cliente_relatorio.py ' + ' '.join(argumentos) + '\n' + resultado.stdout)
        # Falha real do upstream: encerra somente o Flask iniciado por esta bateria.
        processos[0].terminate()
        processos[0].wait(timeout=5)
        verificar('Proxy com Flask desligado', 'GET', 3000, '/api/full-info/1', 502)
        verificar('Cadastro com Flask desligado', 'POST', 3000, '/cadastrar', 502, json={**produto, 'id': '4'})
        verificar('Sem gravação comercial na falha', 'GET', 3000, '/estoque/4', 404)
        (EVIDENCIAS / 'cliente.txt').write_text('\n'.join(saidas), encoding='utf-8')
        ambiente = {'data': datetime.now().astimezone().isoformat(), 'python': sys.version,
                    'node': subprocess.check_output(['node', '--version'], text=True).strip(),
                    'flask': __import__('importlib.metadata', fromlist=['version']).version('flask'),
                    'requests': requests.__version__, 'verificacoes_http': len(registros)}
        (EVIDENCIAS / 'ambiente.json').write_text(json.dumps(ambiente, ensure_ascii=False, indent=2), encoding='utf-8')
        (EVIDENCIAS / 'execucoes.json').write_text(json.dumps(registros, ensure_ascii=False, indent=2), encoding='utf-8')
        texto = '\n\n'.join(f"{r['teste']}\n{r['metodo']} {r['url']}\nHTTP {r['http']}\n{json.dumps(r['resposta'], ensure_ascii=False)}" for r in registros)
        (EVIDENCIAS / 'execucoes.txt').write_text(texto, encoding='utf-8')
        print(f'{len(registros)} verificações HTTP e 5 execuções do cliente aprovadas.')
    finally:
        for processo in processos:
            if processo.poll() is None:
                processo.terminate()
                processo.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == '__main__':
    executar()
