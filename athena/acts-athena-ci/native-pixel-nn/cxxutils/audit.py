#!/usr/bin/env python3
"""Audit ISA separation without modifying any object or shared library."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

OUT = Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils')
selected = json.loads((OUT / 'selected.json').read_text())
record = {}
for compiler, choice in selected.items():
    folder = OUT / compiler
    row = {}
    for name in ['Activation.o', 'Loader.o', 'Dispatch.o', f'Sse_b{choice["sse"]}.o', f'Avx2_b{choice["avx2"]}.o']:
        path = folder / name
        asm = subprocess.check_output(['objdump', '-drC', '--no-show-raw-insn', str(path)], text=True)
        (folder / (name + '.asm')).write_text(asm)
        instructions = re.findall(r'^\s*[0-9a-f]+:\s+([a-z][a-z0-9]*)\s', asm, re.M)
        avx = sorted({op for op in instructions if op.startswith('v')})
        if not name.startswith('Avx2'): assert not avx, (compiler, name, avx)
        else: assert 'ymm' in asm and any(op.startswith('vfmadd') for op in avx)
        symbols = subprocess.check_output(['nm', '-C', str(path)], text=True)
        if name.startswith(('Sse', 'Avx2')): assert 'Eigen::' not in symbols
        row[name] = {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                     'avx_mnemonics':avx, 'eigen_symbols':'Eigen::' in symbols}
    record[compiler] = row
(OUT / 'isa-audit.json').write_text(json.dumps(record, indent=2) + '\n')
print('GCC/Clang: baseline objects contain no AVX; AVX2 kernels use YMM/FMA and have no Eigen symbols.')
