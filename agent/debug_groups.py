import sys
from pathlib import Path
sys.path.append(r'D:\AI\tools\agent')
from purge_versions import get_g
root = r'D:\AI\tools\agent\test_purge_dir'
print(f"Testing root: {root}")
grps, sings = get_g(root)
print("Groups:", grps)
print("Singles:", sings)
