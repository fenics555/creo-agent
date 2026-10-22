import sys
def write(path, hex_data, mode='w'):
    mode_flag = 'wb' if mode == 'w' else 'ab'
    with open(path, mode_flag) as f:
        f.write(bytes.fromhex(hex_data))
if __name__ == "__main__":
    write(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv)>3 else 'w')
