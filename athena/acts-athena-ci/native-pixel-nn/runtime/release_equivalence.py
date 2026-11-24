#!/usr/bin/env python3
"""Compare all loaded ELF sections, excluding the nonfunctional build identifier."""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
out = root/'run/native-pixel-nn/runtime-mr'
libraries = {
    'gcc': root/'athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib/libSiClusterizationToolLib.so',
    'clang': out/'standalone/clang/libNativeRuntime.so',
}
def sections(path):
    raw = path.read_bytes()
    assert raw[:6] == b'\x7fELF\x02\x01'
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    headers = [struct.unpack_from('<IIQQQQIIQQ', raw, header[6]+i*header[11]) for i in range(header[12])]
    strings = headers[header[13]]
    names = raw[strings[4]:strings[4]+strings[5]]
    result = {}
    for section in headers:
        name = names[section[0]:names.index(0, section[0])].decode()
        if not section[2] & 2 or name == '.note.gnu.build-id':
            continue
        # NOBITS sections allocate zeroed memory without file contents.
        payload = b'' if section[1] == 8 else raw[section[4]:section[4]+section[5]]
        result[name] = {'address': section[3], 'size': section[5], 'flags': section[2],
                        'sha256': hashlib.sha256(payload).hexdigest()}
    return result

state = {'source_commit': subprocess.check_output(['git','-C',str(root/'athena-native-pixel-nn'),'rev-parse','HEAD'],text=True).strip(),
         'libraries': {compiler: {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                  'loaded_sections': sections(path)} for compiler, path in libraries.items()}}
if sys.argv[1] == 'before':
    assert not (out/'release-before.json').exists()
    (out/'release-before.json').write_text(json.dumps(state,indent=2)+'\n')
else:
    before = json.loads((out/'release-before.json').read_text())
    equal = {compiler: before['libraries'][compiler]['loaded_sections'] == entry['loaded_sections'] for compiler,entry in state['libraries'].items()}
    result = {'measured_source_commit': before['source_commit'], 'final_source_commit': state['source_commit'],
              'loaded_sections_identical_except_build_id': equal,
              'before': before, 'after': state}
    (out/'release-equivalence.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(equal,indent=2))
    assert all(equal.values()), 'Loaded code/data changed; repeat affected measurements'
