#!/usr/bin/env python3
"""Check both within-library and cross-library Eigen symbol isolation."""
import hashlib,json,re,subprocess
from pathlib import Path
OUT=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils/tuning')
record={}
def symbols(path):
    text=subprocess.check_output(['nm','-g','--defined-only',str(path)],text=True)
    return {line.split()[-1] for line in text.splitlines() if 'Eigen' in line}
for compiler in ['gcc','clang']:
    record[compiler]={}
    for case in sorted(p.stem.removeprefix('Sse_') for p in (OUT/compiler).glob('Sse_*.o')):
        paths=[OUT/compiler/f'{isa}_{case}.o' for isa in ['Sse','Avx2']]
        overlap=symbols(paths[0]) & symbols(paths[1]); assert not overlap,(compiler,case,overlap)
        dynamic=subprocess.check_output(['nm','-DC','--defined-only',str(OUT/compiler/f'libTune_{case}.so')],text=True)
        assert 'Eigen::' not in dynamic,(compiler,case,dynamic)
        row={'overlapping_eigen_symbols':0,'exported_eigen_symbols':0,'objects':{}}
        for path in paths:
            asm=subprocess.check_output(['objdump','-drC','--no-show-raw-insn',str(path)],text=True)
            (path.with_suffix('.asm')).write_text(asm)
            ops=re.findall(r'^\s*[0-9a-f]+:\s+([a-z][a-z0-9]*)\s',asm,re.M)
            avx=sorted({op for op in ops if op.startswith('v')})
            if path.name.startswith('Sse'): assert not avx,(compiler,case,avx)
            else: assert 'ymm' in asm and any(op.startswith('vfmadd') for op in avx)
            row['objects'][path.name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'avx_mnemonics':avx,'global_eigen_symbol_count':len(symbols(path))}
        record[compiler][case]=row
(OUT/'isa-audit.json').write_text(json.dumps(record,indent=2)+'\n')
print('All variants: no overlapping/exported Eigen symbols; SSE objects contain no AVX.')
