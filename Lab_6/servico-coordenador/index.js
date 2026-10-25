'use strict';
const express = require('express');
const { randomUUID } = require('node:crypto');
const app = express();
app.use(express.json({ limit: '16kb' }));
const locks = new Map();
function log(event, resource) {
  console.log(JSON.stringify({timestamp_utc: new Date().toISOString(),
    level: 'INFO', service: 'servico-coordenador', event, resource}));
}
app.get('/health', (_req, res) => res.json({status: 'ok'}));
app.post('/lock', (req, res) => {
  const resource = req.body?.resource;
  if (typeof resource !== 'string' || !resource.trim() || resource.length > 200)
    return res.status(400).json({error: 'resource deve ser texto de 1 a 200 caracteres'});
  log('Recebido pedido de lock', resource);
  if (locks.has(resource)) {
    log('Recurso em uso, negando lock', resource);
    return res.status(409).json({error: 'Recurso ocupado'});
  }
  const token = randomUUID();
  locks.set(resource, token);
  log('Lock concedido', resource);
  return res.json({resource, token});
});
app.post('/unlock', (req, res) => {
  const {resource, token} = req.body || {};
  if (typeof resource !== 'string' || typeof token !== 'string')
    return res.status(400).json({error: 'resource e token obrigatorios'});
  if (!locks.has(resource) || locks.get(resource) !== token)
    return res.status(409).json({error: 'Lock inexistente ou token incorreto'});
  locks.delete(resource);
  log('Lock liberado', resource);
  return res.json({released: true});
});
app.use((err, _req, res, _next) => res.status(400).json({error: 'JSON invalido'}));
app.listen(Number(process.env.PORT || 3000), '0.0.0.0', () => log('Coordenador iniciado', null));
