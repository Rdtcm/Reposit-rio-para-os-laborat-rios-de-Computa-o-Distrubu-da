import assert from 'node:assert/strict';
import {mkdirSync, writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const evidence = path.join(root, 'evidencias');
mkdirSync(evidence, {recursive: true});
const results = {executado_em_utc: new Date().toISOString(), testes: []};
const mode = process.argv[2] || 'todos';
const api = 'http://127.0.0.1:5000';
const coord = 'http://127.0.0.1:3000';
let slot = Date.now() + 86400000;
function payload(start = (slot += 3600000)) {
  return {cientista_id: 1, telescopio_id: 1,
    horario_inicio_utc: new Date(start).toISOString(),
    horario_fim_utc: new Date(start + 300000).toISOString(),
    timestamp_cliente_utc: new Date().toISOString()};
}
async function req(base, route, method = 'GET', data) {
  const response = await fetch(base + route, {method, signal: AbortSignal.timeout(25000),
    headers: data === undefined ? {'Connection': 'close'} : {'Content-Type': 'application/json', 'Connection': 'close'},
    body: data === undefined ? undefined : JSON.stringify(data)});
  return {status: response.status, body: await response.json(), location: response.headers.get('location')};
}
function record(nome, data) {
  results.testes.push({nome, ...data});
  console.log(JSON.stringify({nome, ...data}, null, 2));
}
async function race(base, label, expected) {
  const data = payload();
  // As dez chamadas sao iniciadas antes de aguardar qualquer resposta.
  const answers = await Promise.all(Array.from({length: 10}, () => req(base, '/agendamentos', 'POST', data)));
  const listing = await req(base, '/agendamentos?inicio=' + encodeURIComponent(data.horario_inicio_utc));
  const statuses = answers.reduce((acc, r) => {acc[r.status] = (acc[r.status] || 0) + 1; return acc;}, {});
  record(label, {entrada: data, codigos: statuses, registros: listing.body.items.length,
    ids: listing.body.items.map(a => a.id), respostas: answers});
  assert.deepEqual(statuses, expected);
  assert.equal(listing.body.items.length, expected[201]);
}
async function contracts() {
  const invalids = [null, [], {}, {...payload(), cientista_id: true},
    {...payload(), cientista_id: 999999}, {...payload(), telescopio_id: 999999},
    {...payload(), horario_inicio_utc: '2026-10-25T12:00:00'},
    {...payload(), horario_fim_utc: '2000-01-01T00:00:00Z'}];
  for (const data of invalids) assert.equal((await req(api, '/agendamentos', 'POST', data)).status, 400);
  const invalidJSON = await fetch(api + '/agendamentos', {method: 'POST',
    headers: {'Content-Type': 'application/json'}, body: '{'});
  assert.equal(invalidJSON.status, 400);
  assert.equal((await req(api, '/agendamentos/999999')).status, 404);
  const scientist = await req(api, '/cientistas', 'POST', {nome: 'Teste de contrato'});
  assert.equal(scientist.status, 201);
  const data = payload();
  data.cientista_id = scientist.body.id;
  const created = await req(api, '/agendamentos', 'POST', data);
  assert.equal(created.status, 201);
  assert.equal(created.location, created.body._links.self.href);
  const read = await req(api, created.body._links.self.href);
  assert.equal(read.body.id, created.body.id);
  const overlap = {...data, horario_inicio_utc: new Date(Date.parse(data.horario_inicio_utc) + 60000).toISOString()};
  assert.equal((await req(api, '/agendamentos', 'POST', overlap)).status, 409);
  const equivalent = {...data, horario_inicio_utc: data.horario_inicio_utc.replace('Z', '+00:00')};
  assert.equal((await req(api, '/agendamentos', 'POST', equivalent)).status, 409);
  const adjacent = {...data, horario_inicio_utc: data.horario_fim_utc,
    horario_fim_utc: new Date(Date.parse(data.horario_fim_utc) + 300000).toISOString()};
  assert.equal((await req(api, '/agendamentos', 'POST', adjacent)).status, 201);
  const cancel = created.body._links.cancelar;
  const cancelled = await req(api, cancel.href, cancel.method);
  assert.equal(cancelled.status, 200);
  assert.equal(cancelled.body.status, 'cancelado');
  assert.equal(cancelled.body._links.cancelar, undefined);
  assert.equal((await req(api, cancel.href, cancel.method)).status, 200);
  assert.equal((await req(api, '/agendamentos', 'POST', data)).status, 201);
  record('Contrato, validacao, sobreposicao e cancelamento HATEOAS', {
    entradas_invalidas: invalids.length + 1, criacao: created, cancelamento: cancelled,
    cancelamento_idempotente: true, reserva_apos_cancelar: true, intervalo_adjacente: true});
}
async function locks() {
  const resource = 'teste-' + Date.now();
  const granted = await req(coord, '/lock', 'POST', {resource});
  assert.equal(granted.status, 200);
  assert.equal((await req(coord, '/lock', 'POST', {resource})).status, 409);
  assert.equal((await req(coord, '/unlock', 'POST', {resource, token: 'incorreto'})).status, 409);
  assert.equal((await req(coord, '/lock', 'POST', {resource})).status, 409);
  assert.equal((await req(coord, '/unlock', 'POST', granted.body)).status, 200);
  const again = await req(coord, '/lock', 'POST', {resource});
  assert.equal(again.status, 200);
  await req(coord, '/unlock', 'POST', again.body);
  record('Coordenador: exclusao e propriedade do token', {aprovado: true});
}
async function clock() {
  const samples = [];
  for (let i = 0; i < 5; i++) {
    const fakeLocal = Date.now() + 2000;
    const begin = performance.now();
    const response = await req(api, '/time');
    const rtt = performance.now() - begin;
    assert.equal(response.status, 200);
    samples.push({rtt_ms: rtt, timestamp_utc: response.body.timestamp_utc,
      offset_ms: response.body.unix_ms + rtt / 2 - (fakeLocal + rtt)});
  }
  const best = [...samples].sort((a, b) => a.rtt_ms - b.rtt_ms)[0];
  record('Cristian: cliente simulado adiantado 2000 ms', {amostras: samples, melhor: best});
  assert.ok(Number.isFinite(best.offset_ms));
  assert.ok(Math.abs(best.offset_ms + 2000) < 500);
}
function docker(...args) {
  return execFileSync('docker', ['compose', ...args], {cwd: root, encoding: 'utf8', timeout: 60000});
}
async function failure() {
  const data = payload();
  let response;
  try {
    docker('stop', 'servico-coordenador');
    response = await req(api, '/agendamentos', 'POST', data);
    assert.equal(response.status, 503);
    const listing = await req(api, '/agendamentos?inicio=' + encodeURIComponent(data.horario_inicio_utc));
    assert.equal(listing.body.items.length, 0);
  } finally { docker('start', '--wait', 'servico-coordenador'); }
  assert.equal((await req(api, '/agendamentos', 'POST', data)).status, 201);
  record('Coordenador indisponivel e recuperacao', {resposta: response, registros_durante_falha: 0, recuperacao: 201});
}
function capture() {
  writeFileSync(path.join(evidence, 'compose-ps.json'), docker('ps', '--format', 'json'));
  writeFileSync(path.join(evidence, 'compose.log'), docker('--profile', 'experimentos', 'logs', '--no-color', '--timestamps'));
  for (const [service, file] of [['servico-agendamento','agenda'], ['demonstracao-sem-lock','sem-lock'], ['demonstracao-com-lock','com-lock']]) {
    writeFileSync(path.join(evidence, file + '.log'), docker('exec', '-T', service, 'cat', '/dados/app.log'));
    const code = `import sqlite3,json; c=sqlite3.connect('/dados/${file}.db'); print(json.dumps({'agendamentos':c.execute('SELECT * FROM agendamento').fetchall(),'auditoria':[json.loads(r[0]) for r in c.execute('SELECT documento FROM auditoria')]},ensure_ascii=False,indent=2))`;
    writeFileSync(path.join(evidence, file + '-banco.json'), docker('exec', '-T', service, 'python', '-c', code));
  }
}
try {
  // Reserve uma faixa posterior aos dados existentes para permitir repeticoes sem apagar volumes.
  for (const base of [api, 'http://127.0.0.1:5001', 'http://127.0.0.1:5002']) {
    const listing = await req(base, '/agendamentos');
    assert.equal(listing.status, 200);
    for (const row of listing.body.items) slot = Math.max(slot, Date.parse(row.horario_fim_utc));
  }
  if (['todos', 'sem-lock'].includes(mode)) await race('http://127.0.0.1:5001', 'Entrega 2: sem lock', {201: 10});
  if (['todos', 'com-lock'].includes(mode)) await race('http://127.0.0.1:5002', 'Entrega 3: com lock', {201: 1, 409: 9});
  if (mode === 'padrao') await race(api, 'Aplicacao padrao: concorrencia sem pausa artificial', {201: 1, 409: 9});
  if (['todos', 'contratos'].includes(mode)) {await contracts(); await locks();}
  if (['todos', 'relogio'].includes(mode)) await clock();
  if (['todos', 'falha'].includes(mode)) await failure();
  if (mode === 'todos') capture();
  results.aprovado = true;
} catch (error) {
  results.aprovado = false;
  results.erro = error.stack;
  console.error(error);
  process.exitCode = 1;
} finally {
  writeFileSync(path.join(evidence, `testes-${mode}.json`), JSON.stringify(results, null, 2));
}
