# -*- coding: utf-8 -*-
"""hf_search.py — поиск моделей на HF по автору/строке (компактно, через API).

    python -X utf8 hf_search.py --author XiaomiMiMo [--limit 50] [--sort downloads]
    python -X utf8 hf_search.py --q mimo-gguf

Печатает: id, downloads, likes, теги-признаки (gguf/moe/mtp/vision/reasoning).
"""
import argparse
import json
import sys
import urllib.parse
import urllib.request


def api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'hf_search/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--author')
    ap.add_argument('--q')
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--sort', default='downloads')
    a = ap.parse_args()

    params = {'limit': a.limit, 'sort': a.sort, 'direction': -1}
    if a.author:
        params['author'] = a.author
    if a.q:
        params['search'] = a.q
    url = 'https://huggingface.co/api/models?' + urllib.parse.urlencode(params)
    try:
        data = api(url)
    except Exception as e:
        print('API FAIL:', type(e).__name__, str(e)[:150])
        return 1
    print('found:', len(data))
    for m in data:
        tags = set(t.lower() for t in (m.get('tags') or []))
        marks = [t for t in ('gguf', 'moe', 'mtp', 'vision', 'reasoning', 'thinking', 'imatrix')
                 if t in tags]
        print('%-58s dl=%-8s likes=%-5s %s'
              % (m['id'][:58], m.get('downloads'), m.get('likes'), ','.join(marks)))
    return 0


if __name__ == '__main__':
    sys.exit(main())