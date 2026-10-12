const express = require('express');
const app = express();
const PORT = 3000;
const FLASK_URL = process.env.FLASK_URL || 'http://localhost:5000';
const produtos_estoque = {
  '1': { nome: 'Dell XPS 13', estoque: 10 },
  '2': { nome: 'Monitor LG 29', estoque: 5 },
};
const produtos_comerciais = produtos_estoque;
const pendentes = new Set();
const invalidId = { error: 'INVALID_ID', message: 'O ID deve ser um inteiro positivo' };
const idValido = id => typeof id === 'string' && /^[0-9]+$/.test(id) && BigInt(id) > 0n;
const normalizar = id => BigInt(id).toString();
app.use(express.json());
app.get('/api/data', (req, res) => res.json({ mensagem: 'Olá do Node.js!', status: 'sucesso', tecnologia: 'JavaScript' }));
app.get('/status', (req, res) => res.json({ service: 'Node.js', status: 'online', timestamp: new Date().toISOString() }));
app.param('id', (req, res, next, id) => {
  if (!idValido(id)) return res.status(400).json(invalidId);
  req.params.id = normalizar(id);
  next();
});
app.get('/estoque/:id', (req, res) => {
  const produto = produtos_estoque[req.params.id];
  if (!produto) return res.status(404).json({ error: 'NOT_FOUND', message: 'Produto não encontrado' });
  res.json(produto);
});
app.get('/api/full-info/:id', async (req, res) => {
  const produto = produtos_estoque[req.params.id];
  if (!produto) return res.status(404).json({ error: 'NOT_FOUND', message: 'Produto não encontrado' });
  try {
    const fiscal = await fetch(`${FLASK_URL}/detalhes/${req.params.id}`, { signal: AbortSignal.timeout(5000) });
    const dados = await fiscal.json();
    if (!fiscal.ok) return res.status(fiscal.status).json(dados);
    res.json({ id: req.params.id, ...produto, ...dados });
  } catch (error) {
    res.status(502).json({ error: 'FISCAL_UNAVAILABLE', message: 'Serviço fiscal indisponível' });
  }
});
app.post('/cadastrar', async (req, res) => {
  const dados = req.body;
  if (!dados || !idValido(dados.id)) return res.status(400).json(invalidId);
  const id = normalizar(dados.id);
  const { nome, estoque, preco_base, categoria } = dados;
  if (typeof nome !== 'string' || !nome.trim() || !Number.isSafeInteger(estoque) || estoque < 0
      || typeof preco_base !== 'number' || !Number.isFinite(preco_base) || preco_base < 0
      || typeof categoria !== 'string' || !categoria.trim()) {
    return res.status(400).json({ error: 'INVALID_DATA', message: 'Dados do produto inválidos' });
  }
  if (produtos_comerciais[id] || pendentes.has(id)) return res.status(409).json({ error: 'ALREADY_EXISTS', message: 'ID já cadastrado' });
  pendentes.add(id);
  try {
    const fiscal = await fetch(`${FLASK_URL}/fiscal/cadastrar`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id, preco_base, categoria }), signal: AbortSignal.timeout(5000),
    });
    const dadosFiscais = await fiscal.json();
    if (fiscal.status !== 201) return res.status(fiscal.ok ? 502 : fiscal.status).json(dadosFiscais);
    produtos_comerciais[id] = { nome: nome.trim().toUpperCase(), estoque };
    res.status(201).json({ id, ...produtos_comerciais[id], ...dadosFiscais });
  } catch (error) {
    res.status(502).json({ error: 'FISCAL_UNAVAILABLE', message: 'Serviço fiscal indisponível' });
  } finally { pendentes.delete(id); }
});
app.use((error, req, res, next) => {
  if (error.type === 'entity.parse.failed') return res.status(400).json({ error: 'INVALID_JSON', message: 'JSON inválido' });
  res.status(error.status || 500).json({ error: 'REQUEST_ERROR', message: 'Falha na requisição' });
});
if (require.main === module) app.listen(PORT, () => console.log(`Servidor Node rodando na porta ${PORT}`));
module.exports = app;
