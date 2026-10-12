#!/usr/bin/env python3
"""Convert the Kosovo acts fetched by xk_fetch.py to Markdown.

Usage: xk_convert.py RAW_DIR OUT_DIR
"""
import datetime, json, os, re, sys, unicodedata
from bs4 import BeautifulSoup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xk_textmd import structure, pdftotext

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()
DIRS = {  # lang: (constitution, codes, laws)
    'sq': ('kushtetuta', 'kode', 'ligje'),
    'sr': ('ustav', 'zakonici', 'zakoni'),
    'en': ('constitution', 'codes', 'laws'),
}
MAIN = re.compile(r'^(LIGJI|LIGJ|KODI|KODIN|KUSHTETUTA)\b', re.I)
CONSTITUTION_ID = 3702
HEADER = re.compile(r'^(GAZETA ZYRTARE|SLUŽBENI LIST|SLUZBENI LIST|OFFICIAL GAZETTE|СЛУЖБЕНИ ЛИСТ|RESMİ GAZETE|'
                    r'TEKSTI I SPASTRUAR|PREČIŠĆENI TEKST|PRECISCENI TEKST|THE CONSOLIDATED TEXT|CONSOLIDATED TEXT)', re.I)
SR_CYR = dict(zip('абвгдђежзијклљмнњопрстћуфхцчџш',
                  ['a', 'b', 'v', 'g', 'd', 'dj', 'e', 'z', 'z', 'i', 'j', 'k', 'l', 'lj', 'm', 'n', 'nj', 'o', 'p',
                   'r', 's', 't', 'c', 'u', 'f', 'h', 'c', 'c', 'dz', 's']))


def slug(s, n=80):
    s = ''.join(SR_CYR.get(c, c) for c in s.lower()).replace('đ', 'dj')
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')[:n].rstrip('-')


def yq(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def dmy(s):
    m = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', s or '')
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None


def text_of(fn):
    pf = fn.replace('.text.html', '.pdf')
    if os.path.exists(pf):
        h = pdftotext(pf).replace('&', '&amp;').replace('<', '&lt;')
        h = '<html><body>' + h.replace('\n', '<br/>') + '</body></html>'
    else:
        h = open(fn, encoding='utf-8', errors='replace').read()
    h = re.sub(r'(?i)<br\s*/?>', '\n', h)
    s = BeautifulSoup(h, 'lxml')
    sp = s.body
    if not sp:
        return ''
    lines = [l.strip() for l in sp.get_text().split('\n')]
    out = []
    for l in lines:
        if HEADER.match(l) or re.fullmatch(r'\d{1,4}', l):
            continue
        out.append(l)
    return structure('\n'.join(out))


def meta_of(fn):
    s = BeautifulSoup(open(fn, encoding='utf-8', errors='replace').read(), 'lxml')
    title = s.title.get_text(' ', strip=True) if s.title else ''
    t = s.body.get_text(' | ', strip=True) if s.body else ''
    rec = {'title': re.sub(r'\s+', ' ', title)}
    for k, labs in (('kind', ('Lloji i aktit:', 'Vrsta akta:', 'Type of act:')),
                    ('number', ('Numri i aktit:', 'Broj akta:', 'Act number:', 'Number of act:')),
                    ('published', ('Data e publikimit:', 'Datum objavljivanja:', 'Date of publication:', 'Publication date:')),
                    ('gazette', ('Gazeta Zyrtare:', 'Službeni list:', 'Official Gazette:'))):
        for lab in labs:
            m = re.search(re.escape(lab) + r' \| ([^|]+)', t)
            if m:
                rec[k] = m.group(1).strip(); break
    rec['repealed'] = bool(re.search(r'\| (Shfuqizuar nga|Ukinut od|Ukinuto od|Repealed by|Abrogated by) \|', t))
    rec['amended_by'] = len(re.findall(r'\| (Ndryshohet/Plotësohet nga|Izmenjen/dopunjen od|Amended/Supplemented by|Amended by) \|', t))
    return rec


def main():
    inforce = [x for x in json.load(open(os.path.join(RAW, 'inforce.json'))) if MAIN.match(x['title'])]
    cons = json.load(open(os.path.join(RAW, 'consolidated.json')))
    byid = {}
    for x in inforce:
        byid.setdefault(x['id'], x)
    # consolidated versions: map by act number to base law
    numre = re.compile(r'(?:NR\.?|NO\.?|BR\.?)\s*([0-9]{2,4}\s*/\s*L?\s*-?\s*[0-9]+|[0-9]{4}/[0-9]+)', re.I)

    def num(t):
        m = numre.search(t or '')
        return re.sub(r'\s+', '', m.group(1)).upper() if m else None
    cons_by_num = {}
    for c in cons:
        n = num(c['title'])
        if 'KUSHTETUT' in c['title'].upper():
            n = 'CONSTITUTION'
        if n:
            cons_by_num.setdefault(n, c)
    counts = {}
    for lang in DIRS:
        d = os.path.join(RAW, lang)
        if not os.path.isdir(d):
            continue
        dc, dk, dl = DIRS[lang]
        done_cons = set()
        jobs = [(x['id'], x, False) for x in byid.values()] + [(CONSTITUTION_ID, {'id': CONSTITUTION_ID}, True)]
        for aid, x, is_const in jobs:
            mfn = os.path.join(d, '%d.meta.html' % aid)
            tfn = os.path.join(d, '%d.text.html' % aid)
            if not os.path.exists(mfn) or not os.path.exists(tfn):
                continue
            meta = meta_of(os.path.join(RAW, 'sq', '%d.meta.html' % aid)) if os.path.exists(os.path.join(RAW, 'sq', '%d.meta.html' % aid)) else meta_of(mfn)
            lmeta = meta_of(mfn)
            if meta['repealed'] and not is_const:
                continue
            n = 'CONSTITUTION' if is_const else num(x.get('title') or meta['title'])
            c = cons_by_num.get(n)
            text_version = 'original'
            src_id = aid
            if c and os.path.exists(os.path.join(d, '%d.text.html' % c['id'])):
                cm = os.path.join(d, '%d.meta.html' % c['id'])
                ctext = text_of(os.path.join(d, '%d.text.html' % c['id']))
                if len(ctext) > 500:
                    text_version = 'consolidated'
                    src_id = c['id']
                    done_cons.add(c['id'])
            md = ctext if text_version == 'consolidated' else text_of(tfn)
            if len(md) < 200:
                continue
            title = (meta_of(os.path.join(d, '%d.meta.html' % src_id))['title'] if text_version == 'consolidated' else lmeta['title']) or x.get('title', '')
            kind = (meta.get('kind') or '').lower()
            pub = dmy(meta.get('published') or x.get('date'))
            year = (pub or '0000')[:4]
            if is_const:
                sub, typ = dc, 'constitution'
            elif kind.startswith('kod') or re.match(r'^(KODI|KODIN)\b', x.get('title', ''), re.I):
                sub, typ = dk, 'code'
            else:
                sub, typ = '%s/%s' % (dl, year), 'act'
            number = meta.get('number') or (n or '')
            fname = '%s-%s-%s.md' % (year, slug(number, 20) or str(aid), slug(re.sub(r'^.*?\d{2,4}\s*/\s*L?\s*-?\s*\d+\s*', '', title) or title, 70))
            path = os.path.join(OUT, lang, sub, fname)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            fm = ['---', 'title: ' + yq(title), 'identifier: ' + yq(number), 'type: ' + typ,
                  'jurisdiction: xk', 'language: ' + lang]
            if pub:
                fm.append('date: ' + pub)
            if text_version == 'consolidated':
                cp = dmy(meta_of(os.path.join(RAW, 'sq', '%d.meta.html' % src_id)).get('published', '')) if os.path.exists(os.path.join(RAW, 'sq', '%d.meta.html' % src_id)) else None
                if cp:
                    fm.append('last_amended: ' + cp)
            fm += ['status: in_force', 'text_version: ' + text_version,
                   ] + (['gazette: ' + yq('Gazeta Zyrtare ' + meta['gazette'])] if meta.get('gazette') else []) + [
                   'source: ' + yq('https://gzk.rks-gov.net/ActDetail.aspx?ActID=%d' % src_id),
                   'retrieved: ' + TODAY]
            if text_version == 'original' and meta.get('amended_by'):
                fm.append('note: ' + yq('Original text as published; amended by %d later act(s) listed on the source page.' % meta['amended_by']))
            if text_version == 'consolidated':
                fm.append('note: ' + yq('Consolidated text published by the Official Gazette as non-official ("Teksti i spastruar i ligjit nuk paraqet version zyrtar").'))
                fm.append('base_act: ' + yq('https://gzk.rks-gov.net/ActDetail.aspx?ActID=%d' % aid))
            fm.append('---')
            open(path, 'w').write('\n'.join(fm) + '\n\n# ' + title + '\n\n' + md + '\n')
            counts[(lang, typ, text_version)] = counts.get((lang, typ, text_version), 0) + 1
    for k, v in sorted(counts.items()):
        print(k, v, file=sys.stderr)


if __name__ == '__main__':
    main()
