"""SCTEC: API REST, coordenacao e trilha de auditoria do laboratorio 6."""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_from_directory, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config.update(SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///agenda.db'),
                  SQLALCHEMY_TRACK_MODIFICATIONS=False,
                  SQLALCHEMY_ENGINE_OPTIONS={'connect_args': {'timeout': 15}},
                  MAX_CONTENT_LENGTH=16384)
db = SQLAlchemy(app)
LOCK_ENABLED = os.getenv('LOCK_ENABLED', 'true').lower() == 'true'
DELAY = float(os.getenv('DEMO_DELAY_SECONDS', '0'))
COORDENADOR = os.getenv('COORDENADOR_URL', 'http://localhost:3000').rstrip('/')
log_path = Path(os.getenv('LOG_PATH', 'app.log'))
log_path.parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger('sctec')
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)sZ %(levelname)s servico-agendamento %(message)s')
formatter.converter = time.gmtime
for handler in (logging.StreamHandler(), logging.FileHandler(log_path, encoding='utf-8')):
    handler.setFormatter(formatter)
    logger.addHandler(handler)


@event.listens_for(Engine, 'connect')
def configure_sqlite(connection, _record):
    connection.execute('PRAGMA foreign_keys=ON')
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('PRAGMA busy_timeout=15000')


class Cientista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)


class Telescopio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)


class Agendamento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cientista_id = db.Column(db.Integer, db.ForeignKey('cientista.id'), nullable=False)
    telescopio_id = db.Column(db.Integer, db.ForeignKey('telescopio.id'), nullable=False)
    horario_inicio_utc = db.Column(db.String(32), nullable=False, index=True)
    horario_fim_utc = db.Column(db.String(32), nullable=False)
    timestamp_cliente_utc = db.Column(db.String(32), nullable=False)
    criado_em_utc = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(16), nullable=False, default='ativo')


class Auditoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    documento = db.Column(db.Text, nullable=False)


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError('Datas devem ser strings ISO 8601 com fuso horario')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Informe o fuso horario nas datas')
    return parsed.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def body():
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError('O corpo deve ser um objeto JSON')
    return data


def link(endpoint, method='GET', **values):
    return {'href': url_for(endpoint, **values), 'method': method}


def representation(a):
    result = {c.name: getattr(a, c.name) for c in Agendamento.__table__.columns}
    result['_links'] = {'self': link('get_agendamento', ident=a.id),
                        'collection': link('list_agendamentos')}
    if a.status == 'ativo':
        result['_links']['cancelar'] = link('cancel_agendamento', 'DELETE', ident=a.id)
    return result


def audit(event_type, a):
    record = {'timestamp_utc': utcnow(), 'level': 'AUDIT', 'event_type': event_type,
              'service': 'servico-agendamento', 'details': {
                  'agendamento_id': a.id, 'cientista_id': a.cientista_id,
                  'telescopio_id': a.telescopio_id,
                  'horario_inicio_utc': a.horario_inicio_utc,
                  'horario_fim_utc': a.horario_fim_utc,
                  'timestamp_cliente_utc': a.timestamp_cliente_utc}}
    encoded = json.dumps(record, ensure_ascii=False)
    db.session.add(Auditoria(documento=encoded))
    return encoded


def acquire(resource):
    logger.info('Tentando adquirir lock para o recurso %s', resource)
    response = requests.post(f'{COORDENADOR}/lock', json={'resource': resource}, timeout=3)
    if response.status_code == 409:
        logger.info('Falha ao adquirir lock, recurso ocupado: %s', resource)
        return None
    response.raise_for_status()
    token = response.json()['token']
    logger.info('Lock adquirido com sucesso: %s', resource)
    return token


def release(resource, token):
    try:
        logger.info('Liberando lock para o recurso %s', resource)
        response = requests.post(f'{COORDENADOR}/unlock',
                                 json={'resource': resource, 'token': token}, timeout=3)
        response.raise_for_status()
    except requests.RequestException:
        logger.exception('Falha ao liberar lock para %s; requer verificacao operacional', resource)


@app.before_request
def log_request():
    logger.info('Requisicao recebida para %s %s', request.method, request.path)


@app.errorhandler(ValueError)
def validation_error(error):
    db.session.rollback()
    return jsonify(error=str(error)), 400


@app.errorhandler(HTTPException)
def http_error(error):
    return jsonify(error=error.description), error.code


@app.errorhandler(requests.RequestException)
def coordinator_error(_error):
    db.session.rollback()
    logger.exception('Coordenador indisponivel; escrita recusada')
    return jsonify(error='Coordenador indisponivel'), 503


@app.errorhandler(SQLAlchemyError)
def database_error(_error):
    db.session.rollback()
    logger.exception('Falha de banco; transacao revertida')
    return jsonify(error='Banco temporariamente indisponivel'), 503


@app.get('/')
def index():
    return send_from_directory('static', 'index.html')


@app.get('/health')
def health():
    db.session.execute(text('SELECT 1'))
    return jsonify(status='ok', lock_enabled=LOCK_ENABLED)


@app.get('/time')
def server_time():
    now = datetime.now(timezone.utc)
    return jsonify(timestamp_utc=now.isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                   unix_ms=now.timestamp() * 1000), 200, {'Cache-Control': 'no-store'}


@app.route('/cientistas', methods=['GET', 'POST'])
def cientistas():
    if request.method == 'POST':
        nome = body().get('nome')
        if not isinstance(nome, str) or not nome.strip() or len(nome) > 120:
            raise ValueError('nome deve conter entre 1 e 120 caracteres')
        c = Cientista(nome=nome.strip())
        db.session.add(c)
        db.session.commit()
        return jsonify(id=c.id, nome=c.nome, _links={'collection': link('cientistas')}), 201
    return jsonify(items=[{'id': c.id, 'nome': c.nome} for c in db.session.scalars(db.select(Cientista))],
                   _links={'self': link('cientistas'), 'criar': link('cientistas', 'POST')})


@app.get('/telescopios')
def telescopios():
    return jsonify(items=[{'id': t.id, 'nome': t.nome} for t in db.session.scalars(db.select(Telescopio))],
                   _links={'self': link('telescopios')})


@app.get('/agendamentos')
def list_agendamentos():
    query = db.select(Agendamento).order_by(Agendamento.id)
    if request.args.get('inicio'):
        query = query.where(Agendamento.horario_inicio_utc == timestamp(request.args['inicio']))
    return jsonify(items=[representation(a) for a in db.session.scalars(query)],
                   _links={'self': link('list_agendamentos'), 'criar': link('create_agendamento', 'POST'),
                           'time': link('server_time')})


@app.get('/agendamentos/<int:ident>')
def get_agendamento(ident):
    return jsonify(representation(db.get_or_404(Agendamento, ident)))


@app.post('/agendamentos')
def create_agendamento():
    data = body()
    for field in ('cientista_id', 'telescopio_id'):
        if type(data.get(field)) is not int or data[field] <= 0:
            raise ValueError(f'{field} deve ser um inteiro positivo')
    start = timestamp(data.get('horario_inicio_utc'))
    end = timestamp(data.get('horario_fim_utc'))
    client_time = timestamp(data.get('timestamp_cliente_utc'))
    if end <= start:
        raise ValueError('O fim deve ser posterior ao inicio')
    # Um lock por telescopio tambem protege intervalos parcialmente sobrepostos.
    resource = f"telescopio-{data['telescopio_id']}"
    token = acquire(resource) if LOCK_ENABLED else None
    if LOCK_ENABLED and token is None:
        return jsonify(error='Recurso ocupado'), 409
    try:
        if LOCK_ENABLED:
            # Segunda defesa persistente: serializa check+insert mesmo apos reinicio do coordenador.
            db.session.execute(text('BEGIN IMMEDIATE'))
        if db.session.get(Cientista, data['cientista_id']) is None:
            raise ValueError('Cientista inexistente')
        if db.session.get(Telescopio, data['telescopio_id']) is None:
            raise ValueError('Telescopio inexistente')
        logger.info('Iniciando verificacao de conflito no BD: %s %s', resource, start)
        conflict = db.session.scalar(db.select(Agendamento.id).where(
            Agendamento.telescopio_id == data['telescopio_id'], Agendamento.status == 'ativo',
            Agendamento.horario_inicio_utc < end, Agendamento.horario_fim_utc > start).limit(1))
        if conflict is not None:
            db.session.rollback()
            return jsonify(error='Horario ja reservado'), 409
        if not LOCK_ENABLED:
            # Apenas a demonstracao vulneravel encerra a leitura antes da escrita.
            db.session.rollback()
        if DELAY:
            time.sleep(DELAY)
        logger.info('Salvando novo agendamento no BD: %s %s', resource, start)
        a = Agendamento(cientista_id=data['cientista_id'], telescopio_id=data['telescopio_id'],
                        horario_inicio_utc=start, horario_fim_utc=end,
                        timestamp_cliente_utc=client_time, criado_em_utc=utcnow(), status='ativo')
        db.session.add(a)
        db.session.flush()
        record = audit('AGENDAMENTO_CRIADO', a)
        result = representation(a)
        db.session.commit()
        logger.warning(record)
        return jsonify(result), 201, {'Location': result['_links']['self']['href']}
    finally:
        db.session.rollback()
        if token:
            release(resource, token)


@app.delete('/agendamentos/<int:ident>')
def cancel_agendamento(ident):
    a = db.get_or_404(Agendamento, ident)
    resource = f'telescopio-{a.telescopio_id}'
    db.session.rollback()
    token = acquire(resource) if LOCK_ENABLED else None
    if LOCK_ENABLED and token is None:
        return jsonify(error='Recurso ocupado'), 409
    try:
        if LOCK_ENABLED:
            db.session.execute(text('BEGIN IMMEDIATE'))
        a = db.get_or_404(Agendamento, ident)
        if a.status == 'cancelado':
            return jsonify(representation(a)), 200
        a.status = 'cancelado'
        record = audit('AGENDAMENTO_CANCELADO', a)
        result = representation(a)
        db.session.commit()
        logger.warning(record)
        return jsonify(result)
    finally:
        db.session.rollback()
        if token:
            release(resource, token)


with app.app_context():
    db.create_all()
    if not db.session.get(Telescopio, 1):
        db.session.add(Telescopio(id=1, nome='Hubble-Acad'))
    if not db.session.get(Cientista, 1):
        db.session.add(Cientista(id=1, nome='Cientista de demonstracao'))
    db.session.commit()
