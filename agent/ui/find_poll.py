import re
with open('D:\\AI\\Tools\\agent\\http_handlers.py', 'r', encoding='utf-8') as f:
    content = f.read()
# Найдем все упоминания chat/poll
for m in re.finditer(r'chat/poll|/chat/poll|poll', content):
    start = max(0, m.start() - 100)
    end = min(len(content), m.end() + 200)
    print(f'--- Pos {m.start()} ---')
    print(content[start:end])
    print()