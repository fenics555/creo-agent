import os
import struct
import re

class CreoBinaryExplorer:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = None
        self.toc = {}
        self._load_and_parse()

    def _load_and_parse(self):
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        
        with open(self.file_path, 'rb') as f:
            self.data = f.read()
        
        self.toc = self._parse_toc()

    def _parse_toc(self):
        toc = {}
        toc_start = self.data.find(b'#UGC_TOC')
        if toc_start == -1:
            return toc
        
        pattern = re.compile(rb'#?([\w]+):\s*([0-9A-Fa-f]+)\s+([0-9A-Fa-f]+)')
        for match in pattern.finditer(self.data[toc_start:]):
            name = match.group(1).decode('ascii')
            offset = int(match.group(2), 16)
            size = int(match.group(3), 16)
            toc[name] = {'offset': offset, 'size': size}
        return toc

    def get_segment_raw(self, segment_name):
        if segment_name not in self.toc:
            return None
        
        info = self.toc[segment_name]
        return self.data[info['offset'] : info['offset'] + info['size']]

    def get_decoded_values(self, segment_name, decoder):
        """
        Returns a list of decoded values from a segment.
        Each value is a dict: {'name': str, 'value': any, 'type': str}
        """
        raw_data = self.get_segment_raw(segment_name)
        if not raw_data:
            return []

        # To decode, we need to know where the segment starts in the WHOLE file
        # because the decoder uses absolute offsets.
        start_offset = self.toc[segment_name]['offset']
        
        results = []
        curr = start_offset
        
        # We need to be careful: the decoder might read past the segment end if not bounded.
        # But for our purpose, we'll just decode until we hit EOF or a type mismatch.
        # A better way is to pass the segment data and the decoder handles it.
        # But current CreoProtocolDecoder expects absolute offsets.
        
        end_offset = start_offset + len(raw_data)
        
        while curr < end_offset:
            val, next_off, v_type, name = decoder.decode_next_value(self.data, curr)
            
            if v_type == "EOF" or next_off == curr:
                break
            
            # If the decoder jumps outside our segment, we stop.
            if next_off > end_offset:
                break

            results.append({
                "name": name,
                "value": val,
                "type": v_type
            })
            curr = next_off
            
        return results
