# -*- coding: utf-8 -*-
"""hf_download.py — скачивание GGUF/HF-файла с докачкой (без сторонних библиотек).

    python -X utf8 hf_download.py --repo DavidAU/<repo> --file <имя.gguf> --out D:\\AI\\ollama\\gguf\\<папка>

Умеет: докачка по Range (повторный запуск продолжает), прогресс каждые 5 %, проверка размера.
ASCII в коде; кириллица не используется.
"""
import argparse
import os
import sys
import time
import urllib.request

API = 'https://huggingface.co'


def human(n):
    if n >= 1e9:
        return '%.2f GB' % (n / 1e9)
    if n >= 1e6:
        return '%.1f MB' % (n / 1e6)
    return '%.0f KB' % (n / 1e3)


def remote_size(url):
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req, timeout=60) as r:
        return int(r.headers.get('Content-Length', 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--file', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--revision', default='main')
    a = ap.parse_args()

    url = '%s/%s/resolve/%s/%s' % (API, a.repo, a.revision, a.file)
    os.makedirs(a.out, exist_ok=True)
    dst = os.path.join(a.out, os.path.basename(a.file))
    total = 0
    try:
        total = remote_size(url)
    except Exception as e:
        print('HEAD failed:', type(e).__name__, str(e)[:120])

    have = os.path.getsize(dst) if os.path.exists(dst) else 0
    if total and have >= total:
        print('ALREADY DONE:', dst, human(have))
        return
    print('URL :', url)
    print('DST :', dst)
    print('size:', human(total) if total else 'unknown', '| have:', human(have))

    req = urllib.request.Request(url, headers={'Range': 'bytes=%d-' % have} if have else {})
    mode = 'ab' if have else 'wb'
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r, open(dst, mode) as f:
        got = have
        last = -1
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total:
                pct = int(got * 100 / total)
                if pct // 5 != last // 5:
                    last = pct
                    speed = got / max(1e-6, (time.time() - t0)) / 1e6
                    print('%3d%%  %s / %s  (%.1f MB/s)' % (pct, human(got), human(total), speed))
    print('DONE:', dst, human(os.path.getsize(dst)))


if __name__ == '__main__':
    sys.exit(main())