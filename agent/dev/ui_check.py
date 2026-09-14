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

if not bad:
    print('ALL GREEN')
else:
    sys.exit(1)
