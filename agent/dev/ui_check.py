import sys

PATHS = [
    (r'D:\AI\tools\agent\ui\app.js', 'app.js'),
    (r'D:\AI\tools\agent\ui\index.html', 'index.html'),
]

bad = False
for p, label in PATHS:
    try:
        with open(p, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print('Error reading file %s: %s' % (label, e))
        sys.exit(1)
    for i, line in enumerate(content.splitlines()):
        if '\\`' in line or '\\${' in line:
            print('%s:%d: %s' % (label, i + 1, line.strip()))
            bad = True

# ===== добавлено 24.09.2026 (вариант 2 окна): баланс JS + опорные элементы витрины =====
# node в системе нет, поэтому баланс скобок/кавычек/шаблонов проверяем сами (толерантный счётчик).
from pathlib import Path as _P

UI = _P(r'D:\AI\tools\agent\ui')


def _js_parts(p):
    t = p.read_text(encoding='utf-8', errors='replace')
    if p.suffix != '.html':
        return t
    parts, i = [], 0
    while True:
        a = t.find('<script', i)
        if a < 0:
            break
        a = t.find('>', a) + 1
        b = t.find('</script>', a)
        if b < 0:
            break
        if 'src=' not in t[max(0, a - 130):a]:
            parts.append(t[a:b])
        i = b + 9
    return '\n'.join(parts)


sys.path.insert(0, str(_P(__file__).parent))
import js_balance  # noqa: E402  (сканер без node: строки/комментарии/регулярки/шаблоны)


def _balance(src):
    return js_balance.balance(src)


for _f in (UI / 'app.js', UI / 'index.html', UI / 'variants' / 'live.js',
           UI / 'variants' / 'v1_tabs.html', UI / 'variants' / 'v2_side.html', UI / 'variants' / 'v3_pult.html'):
    if not _f.exists():
        print('НЕТ ФАЙЛА: %s' % _f)
        bad = True
        continue
    _err = _balance(_js_parts(_f))
    if _err:
        print('%s: JS не сбалансирован — %s' % (_f.name, _err))
        bad = True

_idx = (UI / 'index.html').read_text(encoding='utf-8', errors='replace')
_app = (UI / 'app.js').read_text(encoding='utf-8', errors='replace')
for _where, _txt, _what in (('index.html', _idx, 'id="rail"'), ('index.html', _idx, 'id="zone"'),
                            ('index.html', _idx, 'data-act="rl"'), ('app.js', _app, 'function showZone'),
                            ('app.js', _app, 'function rlJobs'), ('app.js', _app, "a=='rl'"),
                            ('app.js', _app, 'jobsload'),
                            ('index.html', _idx, 'id="tabs"'), ('index.html', _idx, 'data-act="lay"'),
                            ('index.html', _idx, 'lay-v1'), ('index.html', _idx, 'lay-v3'),
                            ('app.js', _app, 'function applyLayout'), ('app.js', _app, 'function zonePult'),
                            ('app.js', _app, 'function fillPstate'), ('app.js', _app, "a=='lay'")):
    if _what not in _txt:
        print('%s: пропал опорный элемент варианта 2: %s' % (_where, _what))
        bad = True
for _where, _txt, _what in (('index.html', _idx, 'wiz_pdf'), ('app.js', _app, 'wiz_pdf'),
                            ('app.js', _app, 'open_pdf_wizard')):
    if _what in _txt:
        print('%s: устаревшее не убрано: %s' % (_where, _what))
        bad = True

if not bad:
    print('ALL GREEN (экранирование, баланс JS, элементы варианта 2)')
else:
    sys.exit(1)
