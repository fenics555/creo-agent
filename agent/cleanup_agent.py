import ast
import os

file_path = 'D:/AI/tools/agent/agent.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.splitlines()

tree = ast.parse(content)

def find_line_range(tree, name, is_class=False):
    for node in ast.walk(tree):
        if is_class and isinstance(node, ast.ClassDef) and node.name == name:
            return node.lineno, node.end_lineno
        if not is_class and isinstance(node, ast.FunctionDef) and node.name == name:
            return node.lineno, node.end_lineno
    return None, None

start_ui, end_ui = find_line_range(tree, '_serve_ui')
start_hd, end_hd = find_line_range(tree, 'Hd', is_class=True)

print(f'UI: {start_ui}-{end_ui}')
print(f'HD: {start_hd}-{end_hd}')

if start_ui and start_hd:
    del lines[start_ui-1 : end_hd]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('Cleanup successful')
else:
    print('Could not find elements to remove')
