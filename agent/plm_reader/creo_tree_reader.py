import json, struct, os, sys, re

def b2h(b): return b.hex()

class CreoTreeUnpacker:
    def __init__(self, p):
        self.p = p
        self.s = os.path.getsize(p)
        with open(p, 'rb') as f: self.d = f.read()
        self.t = {"file": os.path.basename(p), "size": self.s, "sections": []}

    def unpack(self):
        o = 0
        while o < self.s:
            h = self.d.find(b'#', o)
            if h == -1:
                if o < self.s:
                    self.t["sections"].append({"type": "trailing", "offset": o, "len": self.s - o, "raw_hex": b2h(self.d[o:])})
                break
            
            if h - 2 > o:
                self.t["sections"].append({"type": "gap", "offset": o, "len": h - 2 - o, "raw_hex": b2h(self.d[o:h-2])})
                o = h - 2
            elif h - 2 < o:
                self.t["sections"].append({"type": "gap", "offset": o, "len": h + 1 - o, "raw_hex": b2h(self.d[o:h+1])})
                o = h + 1
                continue
            else:
                o = h - 2
            
            try:
                l = struct.unpack('>H', self.d[o:o+2])[0]
                so = o
                se = o + l
                if se > self.s: se = self.s
                ns = o + 3
                ne = self.d.find(b'\0', ns)
                if ne == -1: ne = self.d.find(b'\n', ns)
                
                if ne != -1 and ns < ne and ns < self.s:
                    raw_name = self.d[ns:ne].decode('ascii', errors='ignore')
                    match = re.search(r'#?([A-Za-z0-9_]+)', raw_name)
                    name = match.group(1) if match else raw_name
                    self.t["sections"].append({"name": name, "offset": so, "len": se - so, "content": self._parse(self.d[so:se])})
                    o = se
                    continue
            except:
                pass
            
            self.t["sections"].append({"type": "gap", "offset": o, "len": h + 1 - o, "raw_hex": b2h(self.d[o:h+1])})
            o = h + 1
        return self.t

    def _parse(self, data):
        n = []; i = 0
        while i < len(data):
            if data[i] == 0xe1:
                if i+1 < len(data) and data[i+1] == 0xe0:
                    tc = data[i+2] if i+2 < len(data) else 0
                    ns = i+3; ne = data.find(b'\0', ns)
                    if ne != -1:
                        n.append({"type": "dict_entry", "tag": "e1e0", "field_type": hex(tc), "name": data[ns:ne].decode('ascii', errors='ignore'), "offset": i, "len": ne-i+1}); i = ne+1; continue
                elif i+1 < len(data) and data[i+1] == 0xf1:
                    n.append({"type": "boundary", "tag": "e1f1", "offset": i, "len": 2}); i += 2; continue
                elif i+1 < len(data) and data[i+1] == 0xe1:
                    n.append({"type": "end", "tag": "e1e1", "offset": i, "len": 2}); i += 2; continue
            elif data[i] == 0xf7:
                if i+1 < len(data):
                    n.append({"type": "idx_link", "tag": "f7", "index": data[i+1], "offset": i, "len": 2}); i += 2; continue
            elif data[i] == 0xe3:
                n.append({"type": "sep", "tag": "e3", "offset": i, "len": 1}); i += 1; continue
            elif data[i] == 0xed:
                if i+8 < len(data):
                    try:
                        v = struct.unpack('>d', data[i+1:i+9])[0]
                        n.append({"type": "double", "tag": "ed", "value": v, "offset": i, "len": 9}); i += 9; continue
                    except: pass
            elif data[i] == 0xf6:
                n.append({"type": "tag", "tag": "f6", "offset": i, "len": 1, "raw_hex": b2h(data[i:i+1])}); i += 1; continue
            
            nm = -1
            for m in [0xe0, 0xe1, 0xe2, 0xe3, 0xed, 0xf1, 0xf6, 0xf7]:
                mp = data.find(m, i)
                if mp != -1:
                    if nm == -1 or mp < nm: nm = mp
            
            if nm == -1:
                rd = data[i:]; n.append({"type": "raw", "offset": i, "len": len(rd), "raw_hex": b2h(rd)}); break
            elif nm == i:
                n.append({"type": "raw", "offset": i, "len": 1, "raw_hex": b2h(data[i:i+1])}); i += 1
            else:
                rl = nm - i
                if rl > 0: n.append({"type": "raw", "offset": i, "len": rl, "raw_hex": b2h(data[i:nm])})
                i = nm
        return n
def get_tree_dict(raw_data):
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(raw_data)
        tmp_path = tmp.name
    try:
        unpacker = CreoTreeUnpacker(tmp_path)
        tree = unpacker.unpack()
        return tree
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
