"""Build the standalone Overleaf source from the maintained teaching notes."""
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent / 'control-system.md'


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(c, c) for c in text)


def inline(text):
    # Protect inline code first; bold emphasis is processed only in prose.
    parts = re.split(r'(`[^`]+`)', text)
    out = []
    for part in parts:
        if part.startswith('`'):
            out.append(r'\texttt{' + escape(part[1:-1]) + '}')
        else:
            chunks = re.split(r'(\*\*.*?\*\*)', part)
            out.extend(r'\textbf{' + escape(s[2:-2]) + '}' if s.startswith('**')
                       else escape(s) for s in chunks)
    return ''.join(out)


def convert(source):
    source = source.replace('## From equations to Python: a guided walkthrough',
                            '@@PART3@@')
    substitutions = {'→': ' -> ', '↔': ' <-> ', '−': '-', '–': '--', '—': '---',
                     '×': ' * ', '±': '+/-', 'Δ': 'Delta ', 'θ': 'theta', '·': '*',
                     'π': 'pi', 'Σ': 'Sigma', '┐': '+', '┼': '+', '┘': '+',
                     '─': '-', '│': '|', '\u00a0': ' '}
    for a, b in substitutions.items():
        source = source.replace(a, b)
    lines, out, i, list_kind = source.splitlines(), [], 0, None

    def close_list():
        nonlocal list_kind
        if list_kind:
            out.append('\\end{' + list_kind + '}')
            list_kind = None

    while i < len(lines):
        line = lines[i]
        if line.startswith('```'):
            close_list()
            lang = line[3:].strip()
            out.append(r'\begin{lstlisting}' + ('[language={}]' if lang == 'text' else ''))
            i += 1
            while i < len(lines) and not lines[i].startswith('```'):
                out.append(lines[i]); i += 1
            out.append(r'\end{lstlisting}')
        elif line.strip() == '$$':
            close_list(); out.append(r'\['); i += 1
            while i < len(lines) and lines[i].strip() != '$$':
                out.append(lines[i]); i += 1
            out.append(r'\]')
        elif line.startswith('|'):
            close_list()
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                row = [s.strip() for s in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+', s) for s in row):
                    rows.append(row)
                i += 1
            widths = ([.15, .40, .35] if len(rows[0]) == 3 else [.16, .19, .19, .22, .14])
            spec = ''.join('p{' + str(w) + r'\textwidth}' for w in widths)
            out.extend([r'\begingroup\small', r'\setlength{\tabcolsep}{3pt}',
                        r'\begin{longtable}{' + spec + '}', r'\toprule'])
            for j, row in enumerate(rows):
                out.append(' & '.join(inline(s) for s in row) + r' \\')
                if j == 0:
                    out.append(r'\midrule\endhead')
            out.extend([r'\bottomrule', r'\end{longtable}', r'\endgroup'])
            continue
        elif line == '@@PART3@@':
            close_list()
            out.extend([r'\clearpage', r'\part{From equations to Python: a guided walkthrough}'])
        elif line.startswith('#'):
            close_list()
            level = len(line)-len(line.lstrip('#'))
            if level != 1:
                command = 'section' if level == 2 else 'subsection'
                title = re.sub(r'^(\d+\.|[A-H]\.)\s+', '', line.lstrip('#').strip())
                out.append('\\' + command + '{' + inline(title) + '}')
        elif re.match(r'^(- |\d+\. )', line):
            kind = 'itemize' if line.startswith('- ') else 'enumerate'
            if list_kind != kind:
                close_list(); out.append('\\begin{' + kind + '}'); list_kind = kind
            out.append(r'\item ' + inline(re.sub(r'^(- |\d+\. )', '', line)))
        else:
            if line.strip():
                close_list()
            out.append(inline(line))
        i += 1
    close_list()
    return '\n'.join(out)


document = ((HERE/'preamble.part').read_text(encoding='utf-8') + '\n'
            + convert(NOTES.read_text(encoding='utf-8')) + '\n'
            + (HERE/'closing.part').read_text(encoding='utf-8'))
(HERE/'offgrid_multi_gfm_teaching.tex').write_text(document, encoding='utf-8')
print('Created standalone LaTeX source:', len(document.split()), 'whitespace-separated words/tokens')
