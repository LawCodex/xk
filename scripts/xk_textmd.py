"""Turn plain text extracted from an official PDF/HTML into structured Markdown.

Generic, language-aware heuristics (no rewording of the text):
- article labels ("Neni 1", "Član 1.", "Члан 1", "Член 1", "Article 1") become #### headings;
- all-caps division lines (PJESA, KREU, TITULLI, DIO, GLAVA, ДЕЛ, ГЛАВА, ...) become ### headings;
- PDF hard line wraps are re-joined into paragraphs; page numbers and form feeds are dropped.
"""
import re
import subprocess

ART = re.compile(r'^(Neni|NENI|Član|ČLAN|Članak|ČLANAK|Члан|ЧЛАН|Член|ЧЛЕН|Article|ARTICLE|Clan|Neneni)\s*\.?\s*'
                 r'(\d+[\s./-]*[a-zA-Zа-яА-Я]?\d*|[IVXLC]{1,7}(?:\s*[a-z])?)\s*\.?\s*(\*+|\d{1,2})?$')
DIVISION = re.compile(r'^(PJESA|KREU|TITULLI|SEKSIONI|NËNKREU|KAPITULLI|DIO|DIJELOVI|GLAVA|POGLAVLJE|ODJELJAK|ODELJAK|'
                      r'ДЕЛ|ГЛАВА|ПОГЛАВЈЕ|ОДДЕЛ|ДИО|ГЛАВА|ОДЈЕЉАК|PART|CHAPTER|SECTION|TITLE|KAPITULL|POGLAVLJE)\b')
LOWER = re.compile(r'[a-zа-яëçčćšžđѓќљњџѕј]')
UPPER = re.compile(r'[A-ZА-ЯËÇČĆŠŽĐЃЌЉЊЏЅЈ]')
END = re.compile(r'[.:;!?»“”"\')]$')
LISTSTART = re.compile(r'^(\(?\d{1,3}[.)]|\(?[a-zа-яë]{1,2}[)]|[-–•●▪]\s|\d+\.\d+)')


def pdftotext(path):
    r = subprocess.run(['pdftotext', '-enc', 'UTF-8', path, '-'], capture_output=True)
    return r.stdout.decode('utf-8', 'replace')


def is_heading(line):
    if len(line) > 160 or not UPPER.search(line) or LOWER.search(line):
        return False
    letters = sum(1 for c in line if c.isalpha())
    return letters >= 3


def structure(text):
    text = text.replace('\r', '\n').replace('\x0c', '\n').replace('­', '').replace('﻿', '')
    raw = [re.sub(r'[ \t ]+', ' ', l).strip() for l in text.split('\n')]
    # drop bare page numbers
    lines = [l for l in raw if not re.fullmatch(r'\d{1,4}|-\s*\d{1,4}\s*-|\d{1,4}\s*/\s*\d{1,4}', l)]
    blocks, cur = [], []

    def flush():
        if cur:
            blocks.append(('p', ' '.join(cur)))
            cur.clear()
    for l in lines:
        if not l:
            flush(); continue
        m = ART.match(l)
        if m:
            flush(); blocks.append(('art', l.rstrip('.').strip() if False else l)); continue
        if DIVISION.match(l) or is_heading(l):
            flush(); blocks.append(('h', l)); continue
        if cur:
            prev = cur[-1]
            if END.search(prev) or LISTSTART.match(l):
                flush()
            elif prev.endswith('-') and l[:1].islower():
                cur[-1] = prev[:-1] + l
                continue
        cur.append(l)
    flush()
    # merge consecutive heading lines (e.g. "KREU I" + "DISPOZITA TË PËRGJITHSHME")
    out = []
    for kind, t in blocks:
        if kind == 'h':
            out.append('### ' + t)
        elif kind == 'art':
            out.append('#### ' + t)
        else:
            if re.match(r'^(#|>|[-+*] |\d+\. )', t):
                t = '\\' + t
            out.append(t)
    return '\n\n'.join(out)
