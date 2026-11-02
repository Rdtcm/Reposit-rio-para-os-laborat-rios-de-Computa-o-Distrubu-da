# Laboratório 7 - Processamento de arquivos com gRPC

Servidor C++17, cliente Python e containers Docker. Implementa as Entregas 1 e 2: CompressPDF, ConvertToTXT, ConvertImageFormat e ResizeImage.

## Executar

No PowerShell, na pasta `Lab_7`, com Docker Desktop em modo Linux:

```powershell
docker compose --profile tools build
docker compose up -d server
docker compose run --rm client health
docker compose run --rm --entrypoint python client /app/testes.py
```

Os testes geram arquivos de exemplo em `arquivos/`, verificam resultados e salvam `evidencias/testes.json`. O servidor grava `evidencias/server.log` continuamente. Uma nova rodada substitui os arquivos de teste; o log é cumulativo. A imagem do cliente precisa ser reconstruída após modificar o código.

## Executar cada serviço

Após os testes criarem os exemplos (ou copiando seus próprios arquivos para `arquivos/`):

```powershell
docker compose run --rm client compress /data/entrada.pdf /data/comprimido.pdf
docker compose run --rm client text /data/entrada.pdf /data/saida.txt
docker compose run --rm client convert /data/imagem.jpg /data/convertida.png --format png
docker compose run --rm client resize /data/imagem.png /data/menor.png --width 400 --height 300
docker compose run --rm client convert /data/imagem.png /data/erro.bin --format exe
docker compose run --rm client compress /data/ausente.pdf /data/erro.pdf
docker compose logs --tail 15 server
```

O cliente recebe seleção de arquivos e parâmetros pela linha de comando. Use `--help` para ajuda. As saídas ficam em `arquivos/` no host. Redimensionamento preserva a proporção, conforme `convert -resize` do enunciado: 200x200 sobre uma imagem 1200x900 produz 200x150. A saída de resize é PNG; conversão aceita PNG, JPG e WEBP. Imagens com múltiplos frames usam o primeiro frame.

## Contrato e decisões

- Cada RPC de arquivo é bidirecional: primeiro uma mensagem `metadata`, depois blocos `content` de 64 KiB. O servidor recebe todo o upload em disco, processa e envia o resultado em blocos. Não precisa carregar o arquivo inteiro em memória.
- `Health` demonstra RPC unário. Erros de processamento usam status gRPC; sucesso exige terminar o stream com OK.
- O exemplo do enunciado usa `stream` dentro de mensagens, o que não é sintaxe Protobuf válida. O contrato corrigido aplica `stream` às assinaturas RPC.
- Upload máximo: 32 MiB. Dimensões: 1 a 8192. Ferramenta externa: limite de 30 segundos. Cliente: deadline de 60 segundos.
- Diretórios `mkdtemp` por requisição evitam colisões. Limpeza por RAII ocorre inclusive nas falhas. `posix_spawnp` passa argumentos separados, sem shell.
- O cliente grava em arquivo temporário e só substitui o destino depois de concluir a RPC, preservando saídas anteriores em caso de erro.
- Logs contêm timestamp UTC, método, nome, código gRPC, mensagem e saída/código da ferramenta. Arquivo inexistente no cliente falha antes da RPC, portanto não aparece no servidor.

## Containers

O servidor é compilado em uma etapa Debian com CMake, protoc e plugin C++; a imagem de execução contém gRPC, Ghostscript, Poppler e ImageMagick, sem compilador. Roda como usuário 10001, com limite de 512 MiB e 2 CPUs. O cliente usa imagem Python separada e gera seus stubs no build.

Os serviços comunicam-se pela rede Compose usando `server:50051`. Somente a porta do servidor é publicada no loopback do host. O cliente aguarda o canal ficar disponível, pois `depends_on` garante ordem, não prontidão. Os uploads temporários ficam no container; logs e resultados persistem por bind mounts. Em host Linux, conceda ao UID 10001 escrita na pasta `evidencias` antes de iniciar.

É um ambiente didático local, sem TLS ou autenticação. Os limites não substituem isolamento de arquivos hostis em produção. Cancelamento é verificado após upload e processamento; a ferramenta já iniciada pode continuar até terminar ou atingir 30 segundos. Compressão não garante diminuição de tamanho de todo PDF.

## Compilar fora do Docker (Linux)

Instale g++, CMake, libgrpc++-dev, libprotobuf-dev, protobuf-compiler-grpc, Ghostscript, poppler-utils e ImageMagick. Depois:

```sh
cmake -S server_cpp -B build
cmake --build build -j2
./build/server
```

Em outro terminal com Python e ambiente virtual:

```sh
pip install -r client_python/requirements.txt
python -m grpc_tools.protoc -Iproto --python_out=client_python --grpc_python_out=client_python proto/file_processor.proto
python client_python/client.py health
```

## Encerrar

```powershell
docker compose down
```

O relatório segue o modelo do Lab_6. `relatorio.md` é a fonte editável; o gerador de PDF não sobrescreve esse arquivo.

Para gerar o PDF, instale `reportlab==4.4.4` e execute `python gerar_relatorio.py`. Enquanto houver marcações de prints, a saída será `relatorio-preliminar.pdf`. Depois de inserir as imagens reais e remover as marcações e o aviso de versão preliminar, a saída será `relatorio.pdf`.
