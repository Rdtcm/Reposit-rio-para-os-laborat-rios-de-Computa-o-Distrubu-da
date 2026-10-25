'use strict';
let serverAnchor = null;
let monotonicAnchor = null;
let createLink = null;
const el = id => document.getElementById(id);
async function api(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${data.error || 'Falha'}`);
  return {data, status: response.status};
}
function now() { return serverAnchor + performance.now() - monotonicAnchor; }
async function sync() {
  el('reservar').disabled = true;
  const samples = [];
  for (let i = 0; i < 5; i++) {
    const begin = performance.now();
    const {data} = await api('/time', {cache: 'no-store'});
    const end = performance.now();
    samples.push({rtt: end - begin, anchor: end, time: data.unix_ms + (end - begin) / 2});
  }
  const best = samples.sort((a, b) => a.rtt - b.rtt)[0];
  serverAnchor = best.time;
  monotonicAnchor = best.anchor;
  el('sincronia').textContent = `Cristian: menor RTT de 5 amostras = ${best.rtt.toFixed(2)} ms; estimativa de incerteza ≈ ±${(best.rtt / 2).toFixed(2)} ms (rede simétrica).`;
  el('reservar').disabled = !createLink;
}
async function refresh() {
  const {data} = await api('/agendamentos');
  createLink = data._links.criar;
  el('agenda').replaceChildren();
  for (const a of data.items) {
    const item = document.createElement('li');
    item.textContent = `#${a.id} · ${a.horario_inicio_utc} até ${a.horario_fim_utc} · ${a.status} `;
    if (a._links.cancelar) {
      const button = document.createElement('button');
      button.textContent = 'Cancelar';
      button.onclick = () => run(async () => {
        const result = await api(a._links.cancelar.href, {method: a._links.cancelar.method});
        el('resultado').textContent = `HTTP ${result.status}: agendamento cancelado.`;
        await refresh();
      });
      item.append(button);
    }
    el('agenda').append(item);
  }
  el('reservar').disabled = serverAnchor === null;
}
async function run(action) {
  try { await action(); } catch (error) { el('resultado').textContent = error.message; }
}
el('sync').onclick = () => run(sync);
el('atualizar').onclick = () => run(refresh);
el('form').onsubmit = event => {
  event.preventDefault();
  run(async () => {
    el('reservar').disabled = true;
    try {
      await sync();
      el('reservar').disabled = true;
      const result = await api(createLink.href, {method: createLink.method,
        headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
          cientista_id: Number(el('cientista').value), telescopio_id: Number(el('telescopio').value),
          horario_inicio_utc: new Date(el('inicio').value).toISOString(),
          horario_fim_utc: new Date(el('fim').value).toISOString(),
          timestamp_cliente_utc: new Date(now()).toISOString()})});
      el('resultado').textContent = `HTTP ${result.status}: reserva #${result.data.id} criada.`;
      await refresh();
    } finally { el('reservar').disabled = serverAnchor === null; }
  });
};
setInterval(() => { if (serverAnchor !== null) el('relogio').textContent = new Date(now()).toISOString(); }, 100);
run(async () => {
  for (const [path, target] of [['/cientistas', 'cientista'], ['/telescopios', 'telescopio']]) {
    const {data} = await api(path);
    for (const row of data.items) el(target).add(new Option(row.nome, row.id));
  }
  await refresh();
  await sync();
});
