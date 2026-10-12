#!/usr/bin/env python3
"""Fetch Kosovo laws from the official Gazeta Zyrtare e Republikës së Kosovës
(https://gzk.rks-gov.net, Office of the Prime Minister).

1. Walk the official "Lista e Ligjeve" (LawInForceList.aspx - list of laws in force) and the list
   of consolidated acts (consolidatedacts.aspx), following ASP.NET paging postbacks.
2. For every act: download the metadata page (ActDetail.aspx) and the text page
   (ActDocumentDetail.aspx) in Albanian, Serbian and English (the language is a session setting,
   switched with the site's own language links).  Only the text container is cached.

Usage: xk_fetch.py [RAW_DIR] [langs, default sq,sr,en]
"""
import html as htmlmod, json, os, re, sys, time
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_raw', 'xk')
LANGS = (sys.argv[2] if len(sys.argv) > 2 else 'sq,sr,en').split(',')
BASE = 'https://gzk.rks-gov.net/'
UA = 'LawCodex/1.0 (+https://github.com/LawCodex)'
LANG_BTN = {'sq': 'ctl00$ctlLang1$lbAlbanian', 'sr': 'ctl00$ctlLang1$lbSerbian', 'en': 'ctl00$ctlLang1$lbEnglish'}
DELAY = 0.5


def session(lang):
    s = requests.Session(); s.headers['User-Agent'] = UA
    r = get(s, BASE + 'LawInForceList.aspx')
    if lang != 'sq':
        r = post(s, BASE + 'LawInForceList.aspx', form(r.text, LANG_BTN[lang]))
    return s


def get(s, url):
    for i in range(6):
        try:
            r = s.get(url, timeout=180)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.RequestException('HTTP %d' % r.status_code)
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            w = 5 * 2 ** i
            print('  retry', url, e, w, file=sys.stderr, flush=True); time.sleep(w)
    raise SystemExit('give up ' + url)


def post(s, url, data):
    for i in range(6):
        try:
            r = s.post(url, data=data, timeout=180)
            if r.status_code >= 500 or r.status_code == 429:
                raise requests.RequestException('HTTP %d' % r.status_code)
            time.sleep(DELAY)
            return r
        except requests.RequestException as e:
            w = 5 * 2 ** i
            print('  retry', url, e, w, file=sys.stderr, flush=True); time.sleep(w)
    raise SystemExit('give up ' + url)


def form(html, target):
    s = BeautifulSoup(html, 'lxml')
    d = {i['name']: i.get('value', '') for i in s.find_all('input') if i.get('name', '').startswith('__')}
    d['__EVENTTARGET'] = target; d['__EVENTARGUMENT'] = ''
    return d


def walk_list(s, page, grid, parse):
    url = BASE + page
    r = get(s, url)
    out, seen_pages = [], 0
    while True:
        rows = parse(r.text)
        if rows and out and all(x in out for x in rows):
            break
        out += rows
        seen_pages += 1
        m = re.search(r"__doPostBack\('(ctl00\$MainContent\$%s\$ctl\d+\$lbNext)'" % re.escape(grid), htmlmod.unescape(r.text))
        if not m or not rows:
            break
        r = post(s, url, form(r.text, m.group(1)))
        if seen_pages % 20 == 0:
            print(page, seen_pages, len(out), file=sys.stderr, flush=True)
    return out


def parse_inforce(html):
    s = BeautifulSoup(html, 'lxml')
    rows = []
    for a in s.find_all('a', id=re.compile(r'gvLawInForce_hlActi_\d+$')):
        tr = a.find_parent('tr')
        spans = [x.get_text(' ', strip=True) for x in tr.find_all('span')]
        rows.append({'id': int(a['href'].split('=')[1]), 'title': a.get_text(' ', strip=True),
                     'number': spans[0] if spans else '', 'date': spans[1] if len(spans) > 1 else '',
                     'gz': spans[2] if len(spans) > 2 else ''})
    return rows


def parse_consolidated(html):
    s = BeautifulSoup(html, 'lxml')
    rows = []
    for a in s.find_all('a', href=re.compile(r'ActDetail\.aspx\?ActID=\d+')):
        if 'rGazeta' not in (a.get('id') or ''):
            continue
        rows.append({'id': int(a['href'].split('=')[1]), 'title': a.get_text(' ', strip=True)})
    return rows


def consolidated_all(s):
    """consolidatedacts.aspx is split by year (postback per year), each with paging."""
    url = BASE + 'consolidatedacts.aspx'
    r = get(s, url)
    years = re.findall(r"__doPostBack\('(ctl00\$MainContent\$rGYears\$ctl\d+\$lbGZRKSYear)',''\)\"[^>]*>\s*(\d{4})", htmlmod.unescape(r.text))
    out = []
    for target, y in years:
        r2 = post(s, url, form(r.text, target))
        while True:
            rows = parse_consolidated(r2.text)
            if rows and all(any(x['id'] == y['id'] for y in out) for x in rows):
                break
            for x in rows:
                x['list_year'] = y
            out += rows
            m = re.search(r"__doPostBack\('(ctl00\$MainContent\$rGazeta\$ctl\d+\$lbNext)'", htmlmod.unescape(r2.text))
            if not m or not rows:
                break
            r2 = post(s, url, form(r2.text, m.group(1)))
        print('consolidated', y, len(out), file=sys.stderr, flush=True)
    return out


def main():
    os.makedirs(RAW, exist_ok=True)
    s = session('sq')
    lf = os.path.join(RAW, 'inforce.json')
    if not os.path.exists(lf):
        json.dump(walk_list(s, 'LawInForceList.aspx', 'gvLawInForce', parse_inforce), open(lf, 'w'), ensure_ascii=False)
    cf = os.path.join(RAW, 'consolidated.json')
    if not os.path.exists(cf):
        json.dump(consolidated_all(s), open(cf, 'w'), ensure_ascii=False)
    ids = sorted({x['id'] for x in json.load(open(lf))} | {x['id'] for x in json.load(open(cf))} | {3702})  # 3702 = Constitution
    print(len(ids), 'acts', file=sys.stderr, flush=True)
    for lang in LANGS:
        d = os.path.join(RAW, lang); os.makedirs(d, exist_ok=True)
        sessions = [session(lang) for _ in range(2)]

        def one(args):
            n, aid = args
            ss = sessions[n % 2]
            for kind, page in (('meta', 'ActDetail.aspx'), ('text', 'ActDocumentDetail.aspx')):
                if kind == 'meta' and lang != 'sq':
                    # titles only; metadata in Albanian is enough
                    pass
                fn = os.path.join(d, '%d.%s.html' % (aid, kind))
                if os.path.exists(fn):
                    continue
                r = get(ss, BASE + page + '?ActID=%d' % aid)
                bs = BeautifulSoup(r.text, 'lxml')
                if kind == 'text':
                    el = bs.find(id='MainContent_txtDocument')
                else:
                    el = bs.find('div', class_='content_main') or bs.body
                title = bs.title.get_text(' ', strip=True) if bs.title else ''
                open(fn + '.tmp', 'w').write('<html><head><title>%s</title></head><body>%s</body></html>'
                                            % (title.replace('<', '&lt;'), str(el) if el else ''))
                os.replace(fn + '.tmp', fn)
        with ThreadPoolExecutor(2) as ex:
            for n, _ in enumerate(ex.map(one, enumerate(ids))):
                if n % 100 == 0:
                    print(lang, n, file=sys.stderr, flush=True)
    print('done', file=sys.stderr)


if __name__ == '__main__':
    main()
