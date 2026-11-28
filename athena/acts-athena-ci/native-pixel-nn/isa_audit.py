#!/usr/bin/env python3
"""Read-only ISA/symbol audit of the native pixel NN objects.

isa_audit.py OUT [--objects NAME=DIR]... [--debug]
Release (default): objdump/nm the dispatcher, factory and both ISA objects of the
Athena build (gcc) and of each --objects DIR (e.g. bench_build.sh OUT/clang).
Asserts no AVX outside the AVX2 kernel, FMA in the AVX2 kernel and no global Eigen
symbols in either ISA object. Writes OUT/isa-audit.json.
--debug: compile both ISA sources with GCC and Clang at -O0 and -O1+ASan/UBSan into
OUT/debug-audit; asserts no AVX in the baseline and that every AVX-bearing global
function is the AVX2 entry or encodes the eight-float vector type (cannot collide with
baseline helpers). Writes OUT/debug-audit/summary.json. Needs bench_env.sh.
"""
import argparse
import json
import os
import re
import subprocess
from pathlib import Path

root = Path(os.environ.get('NATIVE_NN_ROOT', '/home/astefl/source/acts/acts-athena-ci'))
package = root/'athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool'
parser = argparse.ArgumentParser()
parser.add_argument('out', type=Path)
parser.add_argument('--objects', action='append', default=[], metavar='NAME=DIR')
parser.add_argument('--debug', action='store_true')
args = parser.parse_args()

def instructions(path):
    return subprocess.check_output(['objdump', '-d', '--no-show-raw-insn', str(path)], text=True)

def release():
    objects = {'gcc': root/'athena-build-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool/CMakeFiles/SiClusterizationToolLib.dir/src'}
    objects.update(item.split('=', 1) for item in args.objects)
    report = {}
    for compiler, directory in objects.items():
        directory = Path(directory)
        report[compiler] = {}
        for name in ['NativePixelClusterNN', 'PixelClusterNNFactory', 'NativePixelClusterNNBaseline', 'NativePixelClusterNNAvx2']:
            path = directory/(name+'.cxx.o')
            if not path.exists():
                path = directory/(name+'.o')
            ops = re.findall(r'^\s*[0-9a-f]+:\s+(\w+)', instructions(path), re.M)
            avx = [op for op in ops if op.startswith('v') and op not in ('verr', 'verw')]
            symbols = subprocess.check_output(['nm', '-gC', '--defined-only', str(path)], text=True)
            eigen = [line for line in symbols.splitlines() if 'Eigen::' in line]
            if name.endswith('Avx2'):
                assert avx and any(op.startswith('vfmadd') for op in avx), path
            else:
                assert not avx, (path, avx)
            if name.endswith(('Baseline', 'Avx2')):
                assert not eigen, (path, eigen)
            report[compiler][name] = {'avx_instructions': len(avx), 'global_eigen_symbols': len(eigen)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'isa-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    return report

def debug():
    out = args.out/'debug-audit'
    lcg = Path(os.environ['NN_STUDY_LCG'])
    includes = ['-I'+str(p) for p in [package, root/'athena-native-pixel-nn/Control/CxxUtils',
                                      lcg/'eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3',
                                      lcg/'Boost/1.91.0/x86_64-el9-gcc15-opt/include']]
    report = {}
    for compiler, cxx in [('gcc', 'g++'), ('clang', os.environ.get('NATIVE_NN_CLANG', '/usr/bin/clang++'))]:
        report[compiler] = {}
        for mode, flags in [('debug', ['-O0']), ('sanitize', ['-O1', '-fsanitize=address,undefined'])]:
            directory = out/compiler/mode
            directory.mkdir(parents=True, exist_ok=True)
            details = {}
            for isa in ['Baseline', 'Avx2']:
                extra = ['-mavx2', '-mfma', '-DEIGEN_MAX_ALIGN_BYTES=16'] if isa == 'Avx2' else []
                path = directory/(isa+'.o')
                subprocess.run([cxx, *flags, '-std=c++23', '-fPIC', '-march=x86-64-v2', '-fvisibility=hidden',
                                '-fvisibility-inlines-hidden', '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))',
                                *extra, *includes, '-c', str(package/f'src/NativePixelClusterNN{isa}.cxx'), '-o', str(path)], check=True)
                symbols = {line.split()[-1] for line in subprocess.check_output(['nm', '-g', '--defined-only', str(path)], text=True).splitlines()}
                name = ''; avx = set()
                for line in instructions(path).splitlines():
                    header = re.match(r'^[0-9a-f]+ <(.*)>:', line)
                    if header: name = header.group(1)
                    if re.match(r'^\s*[0-9a-f]+:\s+v\w+', line): avx.add(name)
                if isa == 'Baseline':
                    assert not avx, (path, avx)
                global_avx = avx & symbols
                assert all('inferAvx2' in s or 'Dv8_f' in s for s in global_avx), (path, global_avx)
                details[isa] = {'avx_bearing_functions': len(avx), 'avx_bearing_global_symbols': sorted(global_avx)}
            report[compiler][mode] = details
    (out/'summary.json').write_text(json.dumps(report, indent=2)+'\n')
    return report

print(json.dumps(debug() if args.debug else release(), indent=2))
