#!/usr/bin/env python3
"""Read-only ISA/symbol audit of the final GCC and Clang objects."""
import json
import os
import re
import subprocess
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
result = Path(os.environ.get('NATIVE_NN_RUN_ROOT', str(root/'run/native-pixel-nn/mr-review')))
objects = {
    'gcc': root/'athena-build-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool/CMakeFiles/SiClusterizationToolLib.dir/src',
    'clang': Path(os.environ.get('NATIVE_NN_CLANG_OBJECT_DIR', str(result/'standalone/clang'))),
}
report = {}
for compiler, directory in objects.items():
    report[compiler] = {}
    for name in ['NativePixelClusterNN',
                 'NativePixelClusterNNBaseline', 'NativePixelClusterNNAvx2']:
        path = directory/(name + ('.cxx.o' if compiler == 'gcc' else '.o'))
        assembly = subprocess.check_output(['objdump', '-d', '--no-show-raw-insn', str(path)], text=True)
        instructions = re.findall(r'^\s*[0-9a-f]+:\s+(\w+)', assembly, re.M)
        avx = [op for op in instructions if op.startswith('v') and op not in ('verr', 'verw')]
        symbols = subprocess.check_output(['nm', '-gC', '--defined-only', str(path)], text=True)
        eigen = [line for line in symbols.splitlines() if 'Eigen::' in line]
        if name.endswith('Avx2'):
            assert avx and any(op.startswith('vfmadd') for op in avx)
        else:
            assert not avx, (path, avx)
        if name.endswith(('Baseline', 'Avx2')):
            assert not eigen, (path, eigen)
        report[compiler][name] = {'avx_instructions': len(avx), 'global_eigen_symbols': len(eigen)}
(result/'isa-audit.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
