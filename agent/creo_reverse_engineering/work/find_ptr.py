import os

path = r'Z:\PTC\Work\001_15 ЦТКД Электон\ЦТКД 738.01.001-01 Фланец\ctkd_738_01_001-01.prt.11'
with open(path, 'rb') as f:
    data = f.read()

pos = data.find(b'id_map_info_ptr')
print(f'Offset: {pos}')
if pos != -1:
    null_pos = data.find(b'\x00', pos)
    print(f'Null pos: {null_pos}')
    if null_pos != -1:
        print(f'Value (4 bytes after null): {data[null_pos+1:null_pos+5].hex()}')
    else:
        print('Null not found')
else:
    print('String not found')
