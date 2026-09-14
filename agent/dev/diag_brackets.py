import re
import sys

def check_balance(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    stack = []
    pairs = {'}': '{', ']': '[', ')': '('}
    idx = 0
    while idx < len(content):
        char = content[idx]
        
        if char in '"\'':
            q = char
            idx += 1
            while idx < len(content) and content[idx] != q:
                if content[idx] == '\\':
                    idx += 1
                idx += 1
            if idx < len(content):
                idx += 1
            continue

        if char in '{[(':
            stack.append((char, idx + 1))
        elif char in '}])':
            if not stack or stack.pop()[0] != pairs[char]:
                print(f"Mismatch at pos {idx + 1}: {char}")
                return
        idx += 1

    if stack:
        print(f"Unclosed: {stack}")
    else:
        print("Balanced")

if __name__ == "__main__":
    check_balance(r'D:\AI\tools\agent\ui\index.html')
