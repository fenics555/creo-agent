import os

file_path = r'D:\AI\tools\agent\loop.py'
if os.path.exists(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace literal \n with actual newline
    fixed = content.replace('\\n', '\n')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed)
    
    print(f"Fixed! Newline count: {fixed.count('\n')}")
else:
    print(f"Error: {file_path} not found")
