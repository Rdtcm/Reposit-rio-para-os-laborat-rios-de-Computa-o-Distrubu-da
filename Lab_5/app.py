from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import re
from flask import Flask, jsonify, request

app = Flask(__name__)
produtos_fiscais = {'1': {'preco': 2500.0, 'categoria': 'Laptops'}, '2': {'preco': 1200.0, 'categoria': 'Monitores'}}
produtos_tecnicos = produtos_fiscais
INVALID_ID = {'error': 'INVALID_ID', 'message': 'O ID deve ser um inteiro positivo'}

def id_valido(id):
    return isinstance(id, str) and re.fullmatch(r'[0-9]+', id) and int(id) > 0

@app.get('/api/data')
def data():
    return jsonify(mensagem='Olá do Flask!', status='sucesso', tecnologia='Python')

@app.get('/detalhes/<id>')
def detalhes(id):
    if not id_valido(id):
        return jsonify(INVALID_ID), 400
    produto = produtos_fiscais.get(str(int(id)))
    if produto is None:
        return jsonify(error='NOT_FOUND', message='Produto não encontrado'), 404
    return jsonify(produto)

@app.get('/status')
def status():
    return jsonify(service='Flask', status='online', timestamp=datetime.now(timezone.utc).isoformat())

@app.post('/fiscal/cadastrar')
def cadastrar():
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict):
        return jsonify(error='INVALID_DATA', message='Envie um objeto JSON'), 400
    if not id_valido(dados.get('id')):
        return jsonify(INVALID_ID), 400
    id = str(int(dados['id']))
    preco, categoria = dados.get('preco_base'), dados.get('categoria')
    if (type(preco) not in (int, float) or not math.isfinite(preco) or preco < 0
            or not isinstance(categoria, str) or not categoria.strip()):
        return jsonify(error='INVALID_DATA', message='Preço e categoria inválidos'), 400
    if id in produtos_fiscais:
        return jsonify(error='ALREADY_EXISTS', message='ID já cadastrado'), 409
    calculado = (Decimal(str(preco)) * Decimal('1.20')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    produtos_tecnicos[id] = {'preco': float(calculado), 'categoria': categoria.strip()}
    return jsonify(produtos_tecnicos[id]), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
