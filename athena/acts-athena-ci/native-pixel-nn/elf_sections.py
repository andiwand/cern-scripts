#!/usr/bin/env python3
"""Read-only ELF64 (little-endian) section tools; never rewrites the inspected file.

elf_sections.py snapshot OUT.json LIB...        record hashes of all loaded sections
elf_sections.py compare BEFORE.json OUT.json    re-read the same libraries, fail if any
                                                loaded section changed (build ID excluded)
elf_sections.py extract LIB SECTION OUT         write one section's raw bytes
Use snapshot/compare to show a rebuild (restore, source cleanup) leaves the measured
code and data unchanged, so earlier measurements still apply.
"""
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

SOURCE = Path('/home/astefl/source/acts/acts-athena-ci/athena-native-pixel-nn')

def headers(raw):
    assert raw[:6] == b'\x7fELF\x02\x01'
    header = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    sections = [struct.unpack_from('<IIQQQQIIQQ', raw, header[6]+i*header[11]) for i in range(header[12])]
    strings = sections[header[13]]
    names = raw[strings[4]:strings[4]+strings[5]]
    for section in sections:
        yield names[section[0]:names.index(0, section[0])].decode(), section

def loaded(path):
    raw = Path(path).read_bytes()
    result = {}
    for name, section in headers(raw):
        if not section[2] & 2 or name == '.note.gnu.build-id':
            continue
        # NOBITS sections allocate zeroed memory without file contents.
        payload = b'' if section[1] == 8 else raw[section[4]:section[4]+section[5]]
        result[name] = {'address': section[3], 'size': section[5], 'flags': section[2],
                        'sha256': hashlib.sha256(payload).hexdigest()}
    return result

def state(paths):
    commit = subprocess.run(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    return {'source_commit': commit,
            'libraries': {str(path): {'sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
                                      'loaded_sections': loaded(path)} for path in paths}}

command, *rest = sys.argv[1:] or ['help']
if command == 'snapshot' and len(rest) >= 2:
    out = Path(rest[0])
    assert not out.exists(), f'Refusing to overwrite {out}'
    out.write_text(json.dumps(state(rest[1:]), indent=2)+'\n')
elif command == 'compare' and len(rest) == 2:
    before = json.loads(Path(rest[0]).read_text())
    after = state(before['libraries'])
    equal = {path: entry['loaded_sections'] == after['libraries'][path]['loaded_sections']
             for path, entry in before['libraries'].items()}
    file_equal = {path: entry['sha256'] == after['libraries'][path]['sha256'] for path, entry in before['libraries'].items()}
    result = {'before_source_commit': before['source_commit'], 'after_source_commit': after['source_commit'],
              'file_hash_identical': file_equal, 'loaded_sections_identical_except_build_id': equal,
              'before': before, 'after': after}
    Path(rest[1]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'file_hash_identical': file_equal, 'loaded_sections_identical_except_build_id': equal}, indent=2))
    sys.exit(0 if all(equal.values()) else 'Loaded code/data changed; repeat affected measurements')
elif command == 'extract' and len(rest) == 3:
    raw = Path(rest[0]).read_bytes()
    section = next((s for name, s in headers(raw) if name == rest[1]), None)
    if section is None:
        sys.exit('Missing ELF section ' + rest[1])
    Path(rest[2]).write_bytes(raw[section[4]:section[4]+section[5]])
else:
    sys.exit(__doc__)
