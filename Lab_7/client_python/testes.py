"""Testes de integracao reais, executados no container cliente."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import grpc
from PIL import Image
from reportlab.pdfgen import canvas
from pypdf import PdfReader
import file_processor_pb2 as pb
import file_processor_pb2_grpc as rpc
from client import transfer

data = Path('/data')
data.mkdir(exist_ok=True)
evidence = Path('/evidencias')
evidence.mkdir(exist_ok=True)
results = []

def case(name, action):
    result = action()
    record = dict(caso=name, aprovado=True, detalhes=result)
    results.append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)

def fixtures():
    image = Image.effect_noise((1200, 900), 70).convert('RGB')
    image.save(data / 'imagem.png')
    image.save(data / 'imagem.jpg')
    doc = canvas.Canvas(str(data / 'entrada.pdf'), pageCompression=0)
    doc.drawString(50, 800, 'Laboratorio 7 - gRPC: teste de processamento de arquivos.')
    doc.drawImage(str(data / 'imagem.jpg'), 50, 100, width=450, height=337)
    doc.save()
    doc = canvas.Canvas(str(data / 'texto.pdf'))
    doc.drawString(50, 800, 'Segundo arquivo PDF para teste.')
    doc.save()
    (data / 'invalido.pdf').write_bytes(b'%PDF-arquivo corrompido')
    (data / 'vazio.pdf').write_bytes(b'')

def expect_error(action, code):
    try:
        action()
    except grpc.RpcError as exc:
        assert exc.code() == code, (exc.code(), exc.details())
        return dict(status=exc.code().name, mensagem=exc.details())
    raise AssertionError('RPC deveria falhar')

fixtures()
started = datetime.now(timezone.utc).isoformat()
try:
    with grpc.insecure_channel(os.getenv('GRPC_SERVER', 'server:50051')) as channel:
        grpc.channel_ready_future(channel).result(timeout=30)
        stub = rpc.FileProcessorServiceStub(channel)
        case('RPC unario Health', lambda: stub.Health(pb.HealthRequest(), timeout=5).status)
        def compress(source):
            dest = data / ('comprimido-' + source)
            size = transfer(stub, 'compress', data / source, dest)
            assert len(PdfReader(dest).pages) == 1
            assert 'teste' in PdfReader(dest).pages[0].extract_text()
            return dict(entrada_bytes=(data / source).stat().st_size, saida_bytes=size)
        for source in ['entrada.pdf', 'texto.pdf']:
            case('CompressPDF ' + source, lambda s=source: compress(s))
        def text(source):
            dest = data / (source + '.txt')
            transfer(stub, 'text', data / source, dest)
            content = dest.read_text()
            assert 'teste' in content
            return dict(texto=content.strip())
        for source in ['entrada.pdf', 'texto.pdf']:
            case('ConvertToTXT ' + source, lambda s=source: text(s))
        def convert(source, fmt):
            dest = data / ('convertido.' + fmt)
            transfer(stub, 'convert', data / source, dest, fmt)
            with Image.open(dest) as image:
                assert image.size == (1200, 900)
                assert image.format == {'png': 'PNG', 'jpg': 'JPEG', 'webp': 'WEBP'}[fmt]
                return dict(formato=image.format, dimensoes=image.size)
        for source, fmt in [('imagem.jpg', 'png'), ('imagem.png', 'jpg'), ('imagem.png', 'webp')]:
            case('ConvertImageFormat ' + fmt, lambda s=source, f=fmt: convert(s, f))
        def resize(width, height):
            dest = data / f'redimensionada-{width}x{height}.png'
            transfer(stub, 'resize', data / 'imagem.png', dest, width=width, height=height)
            with Image.open(dest) as image:
                expected = (400, 300) if width == 400 else (200, 150)
                assert image.size == expected
                return dict(limites=[width, height], dimensoes=image.size)
        case('ResizeImage 400x300', lambda: resize(400, 300))
        case('ResizeImage preserva proporcao 200x200', lambda: resize(200, 200))
        for title, operation, source, params in [
            ('PDF corrompido', 'compress', 'invalido.pdf', {}),
            ('PDF vazio', 'text', 'vazio.pdf', {}),
            ('Imagem como PDF', 'text', 'imagem.png', {}),
            ('Formato invalido', 'convert', 'imagem.png', {'output_format':'exe'}),
            ('Dimensao invalida', 'resize', 'imagem.png', {'width':0, 'height':100}),
            ('Imagem corrompida', 'convert', 'invalido.pdf', {'output_format':'png'}),
        ]:
            def invalid(op=operation, src=source, kw=params):
                dest = data / 'preservado.txt'
                dest.write_text('preservar')
                result = expect_error(lambda: transfer(stub, op, data/src, dest, **kw), grpc.StatusCode.INVALID_ARGUMENT)
                assert dest.read_text() == 'preservar'
                assert not list(data.glob('*.part'))
                return result
            case(title, invalid)
        def missing():
            try:
                transfer(stub, 'compress', data/'ausente.pdf', data/'nao-gerado.pdf')
            except FileNotFoundError:
                return 'FileNotFoundError local; nenhuma RPC enviada'
            raise AssertionError('Arquivo ausente aceito')
        case('Arquivo nao encontrado', missing)
        case('Stream sem metadata', lambda: expect_error(lambda: list(stub.CompressPDF(iter([pb.FileRequest(content=b'abc')]), timeout=5)), grpc.StatusCode.INVALID_ARGUMENT))
        case('Nome com caminho', lambda: expect_error(lambda: list(stub.CompressPDF(iter([pb.FileRequest(metadata=pb.Metadata(file_name='../escape.pdf'))]), timeout=5)), grpc.StatusCode.INVALID_ARGUMENT))
        case('Metadata repetida', lambda: expect_error(lambda: list(stub.CompressPDF(iter([pb.FileRequest(metadata=pb.Metadata(file_name='a.pdf'))]*2), timeout=5)), grpc.StatusCode.INVALID_ARGUMENT))
        def large():
            def chunks():
                yield pb.FileRequest(metadata=pb.Metadata(file_name='grande.pdf'))
                for _ in range(513):
                    yield pb.FileRequest(content=b'x'*65536)
            return expect_error(lambda: list(stub.CompressPDF(chunks(), timeout=15)), grpc.StatusCode.RESOURCE_EXHAUSTED)
        case('Limite de upload 32 MiB', large)
        def concurrent():
            def job(i):
                dest = data / f'concorrente-{i}.txt'
                transfer(stub, 'text', data/'texto.pdf', dest)
                assert 'Segundo arquivo' in dest.read_text()
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(job, range(4)))
            return '4 chamadas com mesmo nome de entrada, resultados independentes'
        case('Concorrencia', concurrent)
finally:
    (evidence/'testes.json').write_text(json.dumps(dict(inicio_utc=started, casos=results), ensure_ascii=False, indent=2))
print(f'APROVADOS: {len(results)} testes')
