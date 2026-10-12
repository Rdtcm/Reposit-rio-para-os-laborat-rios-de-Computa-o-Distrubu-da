# Lab_5 - Web Services

Implementação dos cinco exercícios de `Aula12IntroWS.pdf`.
Requer Node.js 18 ou superior (fetch nativo) e Python com Flask e requests.

Na raiz do repositório:

```powershell
.\.venv\Scripts\python.exe -m pip install -r Lab_5/requirements.txt
cd Lab_5
npm.cmd ci
```

Abra dois terminais, a partir da raiz do repositório:

```powershell
.\.venv\Scripts\python.exe Lab_5/app.py
```

```powershell
cd Lab_5
npm.cmd start
```

No terceiro terminal, na raiz:

```powershell
.\.venv\Scripts\python.exe Lab_5/cliente_relatorio.py
.\.venv\Scripts\python.exe Lab_5/cliente_relatorio.py --status
Invoke-RestMethod http://localhost:3000/api/full-info/1
Invoke-RestMethod -Method Post -Uri http://localhost:3000/cadastrar -ContentType 'application/json' -Body '{"id":"3","nome":"teclado","estoque":20,"preco_base":200.0,"categoria":"Perifericos"}'
Invoke-RestMethod http://localhost:3000/api/full-info/3
```

Teste de erro: `curl.exe -i http://localhost:3000/estoque/-5`.
Ambos os serviços oferecem `/api/data` e `/status`; o Flask oferece
`/detalhes/<id>` e `/fiscal/cadastrar`; o Node oferece `/estoque/:id`,
`/api/full-info/:id` e `/cadastrar`.

Os cadastros ficam em memória e são perdidos ao reiniciar os servidores.
Os IDs são strings com inteiros positivos. IDs ausentes retornam 404,
inválidos retornam 400, duplicados retornam 409 e falha do Flask retorna 502 no Node.

Para repetir os experimentos, encerre os servidores manuais e execute na raiz:

```powershell
.\.venv\Scripts\python.exe Lab_5/executar_experimentos.py
```

O script inicia e encerra seus próprios processos, confirma os resultados por HTTP
e salva registros em `Lab_5/evidencias/`. Não altera serviços já existentes.
Para regenerar o PDF (requer reportlab e pymupdf na venv):

```powershell
.\.venv\Scripts\python.exe Lab_5/gerar_relatorio.py
```

O relatório usa os modelos do Lab_3 e Lab_4 e inclui nove capturas reais em `prints/`.
O gerador lê `relatorio.md`, preserva suas edições e incorpora as imagens referenciadas.
Se uma imagem estiver ausente, informa o caminho antes de gerar o PDF.
