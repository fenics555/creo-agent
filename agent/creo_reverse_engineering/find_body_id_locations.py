import sys
import os

sys.path.insert(0, 'D:/AI/tools/agent')
from plm_reader.creo_read import read
import re

def find_body_id_locations(file_path):
    data = read(file_path)
    matches = list(re.finditer(b'body_id', data))
    print(f"Found {len(matches)} occurrences of 'body_id'")
    for m in matches:
        start = m.start()
        print(f"Offset {start}: {data[start:start+50].hex(' ')}")

if __name__ == "__main__":
    find_body_id_locations('D:/AI/PROBA/models/00080-03.prt')
