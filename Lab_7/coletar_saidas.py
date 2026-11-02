"""Executa os casos e preserva stdout/stderr completos, comandos e exit codes."""
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess

BASE = Path(__file__).resolve().parent
started = datetime.now(timezone.utc)
folder = BASE / 'evidencias' / ('terminal-' + started.strftime('%Y%m%dT%H%M%SZ'))
folder.mkdir()
records = []

def run(name, args, expected=0):
    command = subprocess.list2cmdline(args)
    result = subprocess.run(args, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            encoding='utf-8', errors='replace')
    record = dict(nome=name, comando=command, saida=result.stdout,
                  codigo_saida=result.returncode, esperado=expected)
    records.append(record)
    transcript = f'$ {command}\n{result.stdout}\n[codigo de saida: {result.returncode}]\n'
    (folder / f'{len(records):02d}-{name}.txt').write_text(transcript, encoding='utf-8')
    (folder/'registros.json').write_text(json.dumps(dict(inicio_utc=started.isoformat(), registros=records), ensure_ascii=False, indent=2), encoding='utf-8')
    print(transcript, flush=True)
    if result.returncode != expected:
        raise RuntimeError(f'{name}: codigo inesperado {result.returncode}')

compose = ['docker', 'compose']
client = compose + ['run', '--rm', '-T', 'client']
inspect = compose + ['run', '--rm', '-T', '--entrypoint', 'python', 'client', '-c']
run('servidor', compose + ['up', '-d', 'server'])
run('containers', compose + ['ps'])
run('health', client + ['health'])
run('testes-completos', compose + ['run', '--rm', '-T', '--entrypoint', 'python', 'client', '/app/testes.py'])
for source in ['entrada', 'texto']:
    run('compressao-' + source, client + ['compress', f'/data/{source}.pdf', f'/data/terminal-{source}.pdf'])
run('verificacao-pdfs', inspect + ["from pathlib import Path; from pypdf import PdfReader; [(print(f'{p.name}: {p.stat().st_size} bytes; paginas={len(PdfReader(p).pages)}; texto={PdfReader(p).pages[0].extract_text()!r}')) for p in [Path('/data/entrada.pdf'),Path('/data/terminal-entrada.pdf'),Path('/data/texto.pdf'),Path('/data/terminal-texto.pdf')]]"])
for source in ['entrada', 'texto']:
    run('extracao-' + source, client + ['text', f'/data/{source}.pdf', f'/data/terminal-{source}.txt'])
    run('conteudo-' + source, inspect + [f"from pathlib import Path; import sys; sys.stdout.write(Path('/data/terminal-{source}.txt').read_text())"])
for fmt in ['png', 'jpg', 'webp']:
    run('conversao-' + fmt, client + ['convert', '/data/imagem.jpg', f'/data/terminal-convertida.{fmt}', '--format', fmt])
run('verificacao-formatos', inspect + ["from PIL import Image; from pathlib import Path; [(print(p.name, Image.open(p).format, Image.open(p).size)) for p in sorted(Path('/data').glob('terminal-convertida.*'))]"])
for width,height in [(400,300),(200,200)]:
    run(f'redimensionamento-{width}x{height}', client + ['resize', '/data/imagem.png', f'/data/terminal-menor-{width}.png', '--width', str(width), '--height', str(height)])
run('verificacao-dimensoes', inspect + ["from PIL import Image; from pathlib import Path; [(print(p.name, Image.open(p).format, Image.open(p).size)) for p in sorted(Path('/data').glob('terminal-menor-*.png'))]"])
for name,args in [
    ('erro-formato',['convert','/data/imagem.png','/data/terminal-erro.bin','--format','exe']),
    ('erro-ausente',['compress','/data/ausente.pdf','/data/terminal-erro.pdf']),
    ('erro-pdf',['compress','/data/invalido.pdf','/data/terminal-erro.pdf']),
    ('erro-vazio',['text','/data/vazio.pdf','/data/terminal-erro.txt']),
    ('erro-dimensao',['resize','/data/imagem.png','/data/terminal-erro.png','--width','0','--height','100'])
]:
    run(name, client + args, expected=1)
run('temporarios', compose + ['exec','-T','server','find','/tmp','-maxdepth','1','-name','lab7-*'])
run('logs-servidor', compose + ['logs','--no-color','--since',started.isoformat(),'server'])
(folder/'terminal-completo.txt').write_text('\n'.join(f"$ {r['comando']}\n{r['saida']}\n[codigo de saida: {r['codigo_saida']}]\n" for r in records), encoding='utf-8')
print('EVIDENCIAS:', folder)
