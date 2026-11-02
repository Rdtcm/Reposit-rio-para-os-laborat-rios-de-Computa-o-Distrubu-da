"""Gera PDF a partir do Markdown, sem sobrescrever edições ou capturas."""
from pathlib import Path
from html import escape
import re
import textwrap
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted, Table, TableStyle, Image, PageBreak

BASE = Path(__file__).resolve().parent
text = (BASE/'relatorio.md').read_text(encoding='utf-8-sig')
pending = 'INSERIR PRINT AQUI' in text
output = BASE/('relatorio-preliminar.pdf' if pending else 'relatorio.pdf')
styles = getSampleStyleSheet()
styles['Normal'].fontSize = 9
styles['Normal'].leading = 12
styles['Normal'].spaceAfter = 7
styles['Code'].fontSize = 8
styles['Code'].leading = 10
styles['Code'].leftIndent = 0
styles['Title'].fontSize = 19
styles['Title'].leading = 23
styles['Heading1'].keepWithNext = True
styles['Heading2'].keepWithNext = True
styles['Heading3'].keepWithNext = True
def markup(value):
    value = escape(value)
    return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', value)
story = []
lines = text.splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    if line == '<!-- nova-pagina -->':
        story.append(PageBreak())
    elif line.startswith('```'):
        block = []
        i += 1
        while i < len(lines) and not lines[i].startswith('```'):
            block.extend(textwrap.wrap(lines[i], 100, replace_whitespace=False, drop_whitespace=False) or [''])
            i += 1
        for offset in range(0, len(block), 12):
            story.append(Preformatted('\n'.join(block[offset:offset+12]), styles['Code']))
        story.append(Spacer(1, 9))
    elif line.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            cells = [c.strip() for c in lines[i].strip('|').split('|')]
            if not all(re.fullmatch(r'[-:]+', c) for c in cells):
                rows.append([Paragraph(markup(c), styles['Normal']) for c in cells])
            i += 1
        table = Table(rows, colWidths=[170, 340], repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5edf5')),('GRID',(0,0),(-1,-1),.3,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story.extend([table, Spacer(1, 9)])
        continue
    elif line.startswith('!['):
        match = re.fullmatch(r'!\[(.*?)\]\((.*?)\)', line)
        if not match or not (BASE/match[2]).is_file():
            raise ValueError('Imagem ausente: ' + line)
        picture = Image(str(BASE/match[2]))
        scale = min(510/picture.imageWidth, 400/picture.imageHeight)
        picture.drawWidth = picture.imageWidth*scale
        picture.drawHeight = picture.imageHeight*scale
        story.extend([picture, Spacer(1,9)])
    elif line.startswith('#'):
        depth = len(line) - len(line.lstrip('#'))
        story.append(Paragraph(markup(line[depth:].strip()), styles[['Title','Heading1','Heading2','Heading3'][min(depth,4)-1]]))
    elif line.strip():
        paragraph = Paragraph(markup(line), styles['Normal'])
        if line.startswith('**INSERIR PRINT'):
            paragraph.keepWithNext = True
        story.append(paragraph)
    i += 1
def footer(canvas, doc):
    canvas.setFont('Helvetica', 8)
    canvas.drawString(42, 25, 'Lab 7 - Ryan Ledo' + (' - Preliminar: prints pendentes' if pending else ''))
    canvas.drawRightString(A4[0]-42, 25, str(doc.page))
SimpleDocTemplate(str(output), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=36, bottomMargin=42).build(story, onFirstPage=footer, onLaterPages=footer)
print(output)
