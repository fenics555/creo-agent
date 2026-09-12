import re
import sys

file_path = r'D:\AI\tools\agent\ui\index.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
except Exception as e:
    print(f'Error reading file: {e}')
    sys.exit(1)

script_match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)

if not script_match:
    print('No <script> block found.')
    sys.exit(0)

script_content = script_match.group(1)
lines = script_content.splitlines()

found_issue = False
for i, line in enumerate(lines):
    if r'\`' in line or r'\${' in line:
        print(f'{i+1}: {line.strip()}')
        found_issue = True

if not found_issue:
    print('ALL GREEN')
else:
    sys.exit(1)
