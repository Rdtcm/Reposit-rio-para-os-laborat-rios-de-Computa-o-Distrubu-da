"""Exporta o Markdown editado para PDF, preservando texto e capturas originais."""
from pathlib import Path
import json
from html import escape
import re

import pymupdf as fitz
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle, KeepTogether, Image, PageBreak

BASE = Path(__file__).resolve().parent


def main():
    texto = (BASE / 'relatorio.md').read_text(encoding='utf-8-sig')
    imagens = re.findall(r'^!\[.*?\]\((.*?)\)\s*$', texto, re.MULTILINE)
    ausentes = [nome for nome in imagens if not (BASE / nome).is_file()]
    if ausentes:
        raise SystemExit('Imagens ainda não disponíveis: ' + ', '.join(ausentes))
    styles = getSampleStyleSheet()
    styles['Normal'].fontName = 'Helvetica'
    styles['Normal'].fontSize = 9.5
    styles['Normal'].leading = 13
    styles['Normal'].spaceAfter = 8
    styles['Code'].fontSize = 8
    styles['Code'].leading = 11
    styles['Heading1'].keepWithNext = True
    styles['Heading2'].keepWithNext = True
    story = []
    lines = texto.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('!['):
            match = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', line.strip())
            if not match:
                raise ValueError(f'Referência de imagem inválida: {line}')
            figura = Image(str(BASE / match.group(2)))
            escala = min(17*cm / figura.imageWidth, 16*cm / figura.imageHeight)
            figura.drawWidth = figura.imageWidth * escala
            figura.drawHeight = figura.imageHeight * escala
            story.extend([figura, Spacer(1, 12)])
        elif line.startswith('```'):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                import textwrap
                block.extend(textwrap.wrap(lines[i], 90, replace_whitespace=False, drop_whitespace=False) or [''])
                i += 1
            story.append(KeepTogether([Preformatted('\n'.join(block), styles['Code'])]))
        elif line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                cells = [c.strip() for c in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[-:]+', c) for c in cells):
                    rows.append([Paragraph(escape(c), styles['Normal']) for c in cells])
                i += 1
            table = Table(rows, colWidths=([4*cm, 13*cm] if len(rows[0]) == 2 else [7*cm, 8*cm, 2*cm]), repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e5edf5')), ('GRID', (0,0), (-1,-1), .3, colors.grey), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('LEFTPADDING', (0,0), (-1,-1), 6)]))
            story.extend([table, Spacer(1, 10)])
            continue
        elif line.startswith('#'):
            if line.startswith('## 8.'):
                story.append(PageBreak())
            level = len(line) - len(line.lstrip('#'))
            story.append(Paragraph(escape(line[level:].strip()), styles[['Title', 'Heading1', 'Heading2'][min(level,3)-1]]))
        elif line.strip():
            paragraph = [line]
            while i+1 < len(lines) and lines[i+1].strip() and not lines[i+1].startswith(('#', '|', '```', '![')):
                i += 1
                paragraph.append(lines[i])
            content = escape(' '.join(paragraph))
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            paragrafo = Paragraph(content, styles['Normal'])
            if paragraph[0].startswith('**Figura '):
                paragrafo.keepWithNext = True
            story.append(paragrafo)
        i += 1
    def rodape(canvas, doc):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(2*cm, 1.2*cm, 'Computação Distribuída - Laboratório 5 - Ryan Ledo')
        canvas.drawRightString(19*cm, 1.2*cm, str(doc.page))
    pdf = BASE / 'relatorio.pdf'
    SimpleDocTemplate(str(pdf), rightMargin=2*cm, leftMargin=2*cm, topMargin=1.8*cm, bottomMargin=2*cm).build(story, onFirstPage=rodape, onLaterPages=rodape)
    renders = BASE / 'tmp' / 'pdfs'
    renders.mkdir(parents=True, exist_ok=True)
    with fitz.open(pdf) as document:
        for index, page in enumerate(document):
            page.get_pixmap(matrix=fitz.Matrix(1.3,1.3)).save(renders / f'pagina-{index+1}.png')
        print(f'PDF gerado e reaberto: {len(document)} páginas')


if __name__ == '__main__':
    main()
