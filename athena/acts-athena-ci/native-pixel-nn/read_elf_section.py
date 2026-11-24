#!/usr/bin/env python3
"""Read an ELF64 little-endian section without modifying the input file."""
import struct,sys
from pathlib import Path
raw=Path(sys.argv[1]).read_bytes()
assert raw[:6] == b'\x7fELF\x02\x01'
h=struct.unpack_from('<16sHHIQQQIHHHHHH',raw)
headers=[struct.unpack_from('<IIQQQQIIQQ',raw,h[6]+i*h[11]) for i in range(h[12])]
s=headers[h[13]];names=raw[s[4]:s[4]+s[5]]
for s in headers:
    name=names[s[0]:names.index(0,s[0])].decode()
    if name==sys.argv[2]:
        Path(sys.argv[3]).write_bytes(raw[s[4]:s[4]+s[5]])
        break
else:raise ValueError('Missing ELF section')
