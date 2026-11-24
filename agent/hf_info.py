# -*- coding: utf-8 -*-
"""hf_info.py — КОМПАКТНЫЙ отчёт по HF-репозиторию через API (без скрапинга страниц).

    python -X utf8 hf_info.py --repo openbmb/MiniCPM-V-4.7-35B-A3B-gguf [--repo ...]
    python -X utf8 hf_info.py --repo <repo> --param-B 35     # для расчёта бит/вес

Зачем: HTML-страницы HF огромные и обрезаются; API /tree даёт точный список файлов и размеры.
Что печатает: архитектура, контекст, лицензия, языки; таблица .gguf файлов (размер, бит/вес,
вердикт по нашей карте 16,3 ГБ); отдельной строкой — mmproj/dspark (vision и черновая голова).
ASCII only; кириллица только в подписях через коды не используется.
"""
import argparse
import json
import re
import sys
import urllib.request

VRAM_GB = 16.3          # наша карта
API = 'https://huggingface.co/api/models/%s'
TREE = 'https://huggingface.co/api/models/%s/tree/main?recursive=true&expand=true'


def api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'hf_info/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def verdict(gb):
    if gb <= VRAM_GB - 1.5:
        return 'FITS (полностью в VRAM)'
    if gb <= 20.5:
        return 'PART (~25-30% в RAM, как gemma4/nex)'
    return 'HEAVY (много в RAM)'


def bpw(gb, params_b):
    if not params_b:
        return '-'
    return '%.2f' % (gb * 8 / params_b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', action='append', required=True)
    ap.add_argument('--param-B', type=float, default=0.0, help='параметров, млрд (для бит/вес)')
    a = ap.parse_args()

    for repo in a.repo:
        print('=' * 78)
        print('REPO:', repo)
        try:
            info = api(API % repo)
        except Exception as e:
            print('  API FAIL:', type(e).__name__, str(e)[:120])
            continue
        g = info.get('gguf') or {}
        arch = g.get('architecture', '?')
        ctx = g.get('context_length', '?')
        lic = (info.get('cardData') or {}).get('license', '?')
        langs = (info.get('cardData') or {}).get('language') or []
        print('  arch=%s | ctx=%s | license=%s | downloads=%s | likes=%s'
              % (arch, ctx, lic, info.get('downloads'), info.get('likes')))
        if langs:
            print('  languages:', ', '.join(langs[:20]))
        print('  tags:', ', '.join([t for t in info.get('tags', []) if len(t) < 40][:14]))

        try:
            tree = api(TREE % repo)
        except Exception as e:
            print('  TREE FAIL:', type(e).__name__, str(e)[:120])
            continue
        ggufs, extra = [], []
        for e in tree:
            p, sz = e.get('path', ''), e.get('size', 0)
            if not p.lower().endswith('.gguf'):
                continue
            gb = sz / 1e9
            low = p.lower()
            if 'mmproj' in low or 'dspark' in low or 'projector' in low:
                extra.append((p, gb))
                continue
            m = re.search(r'(IQ\d[_A-Z]*|Q\d[_A-Z]*|F16|BF16|MXFP4)', p, re.I)
            tag = m.group(1) if m else '?'
            ggufs.append((gb, tag, p))

        # 24.11.2026: ШИНЫ (shards) складываем — у больших моделей файл разбит на N частей,
        # и поштучный размер вводил в заблуждение. Группируем по кванту (+ MTP-драфт отдельно).
        groups = {}
        for gb, tag, p in ggufs:
            low = p.lower()
            suffix = ' +MTP' if ('mtp' in low or 'draft' in low) else ''
            key = (tag.upper() + suffix, suffix)
            g = groups.setdefault(key, [0.0, 0, p])
            g[0] += gb
            g[1] += 1
            # 24.11.2026: держим имя первого шина (для точной закачки hf_download.py --file)
            if '-00001-of-' in p or (g[1] == 1 and '-of-' not in g[2]):
                g[2] = p
        print('  %-14s %-8s %-9s %s' % ('quant', 'GB(сумма)', 'bit/wt', 'вердикт (шин)'))
        for (key, suffix), (total, n, sample) in sorted(groups.items(), key=lambda kv: kv[1][0]):
            print('  %-14s %-8.2f %-9s %s  (%d файл.)'
                  % (key, total, bpw(total, a.param_B), verdict(total), n))
            print('        file: %s' % sample.split('/')[-1])
        for p, gb in extra:
            print('  + %.2f GB  %s' % (gb, p.split('/')[-1]))


if __name__ == '__main__':
    sys.exit(main())