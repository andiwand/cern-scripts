#!/usr/bin/env python3
"""Ablate SiLU (default) or dense-loop (--dense) hints. Run after env.sh."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys

root = Path('/home/astefl/source/acts/acts-athena-ci')
package = root / 'athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool'
dense_review = sys.argv[1:] == ['--dense']
assert not sys.argv[1:] or dense_review
output = root / 'run/native-pixel-nn' / ('dense-unroll-review' if dense_review else 'unroll-review')
here = Path(__file__).resolve().parent
inputs = root / 'run/nn-inference/captured-inputs.bin'
external = Path(os.environ['NN_STUDY_EXTERNALS'])
lcg = Path(os.environ['NN_STUDY_LCG'])
include = [package, external / 'include', root / 'athena-native-pixel-nn/Control/CxxUtils',
           lcg / 'eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3',
           lcg / 'Boost/1.91.0/x86_64-el9-gcc15-opt/include']
flags = ['-O2', '-DNDEBUG', '-std=c++23', '-fPIC', '-march=x86-64-v2']
flags += ['-I' + str(path) for path in include]
shared = ['-L' + str(external / 'lib'), '-lonnxruntime', '-Wl,-rpath,' + str(external / 'lib')]
kernel = (package / 'src/NativePixelClusterNNKernel.icc').read_text()
guard = '#ifdef __AVX2__\n#pragma GCC unroll 4\n#endif\n'
plain_kernel = kernel.replace(guard, '')
activation_loop = '  for (unsigned i = 0; i < x.size(); i += Width) {'
assert '#pragma GCC unroll 4' not in plain_kernel and plain_kernel.count(activation_loop) == 1
if dense_review:
    plain = kernel.replace('#pragma GCC unroll 8\n', '')
    accumulation = '\n    for (unsigned k = 0; k < Blocks; ++k) {'
    stores = '\n  for (unsigned k = 0; k < Blocks; ++k) {'
    assert plain.count(accumulation) == plain.count(stores) == 1
    accumulate = plain.replace(accumulation, '\n#pragma GCC unroll 8' + accumulation)
    variants = {'both': accumulate.replace(stores, '\n#pragma GCC unroll 8' + stores), 'accumulate': accumulate,
                'store': plain.replace(stores, '\n#pragma GCC unroll 8' + stores), 'none': plain}
else:
    variants = {'plain': plain_kernel, 'unroll': plain_kernel.replace(activation_loop, '#pragma GCC unroll 4\n' + activation_loop)}
reference = next(iter(variants))
output.mkdir(exist_ok=True)
manifest = dict(source=subprocess.check_output(['git', '-C', str(package), 'rev-parse', 'HEAD'], text=True).strip(),
                cpu=Path('/proc/cpuinfo').read_text().split('model name\t: ')[1].splitlines()[0],
                flags=flags, variants={name: hashlib.sha256(text.encode()).hexdigest() for name, text in variants.items()},
                description='Dense accumulation/store hints separately and together' if dense_review else 'SiLU hint off/on',
                sample='Number + selected position; 100k captured inputs x5 repeats; seven alternating cycles; core 16',
                compiler_versions={}, kernel_sha256=hashlib.sha256(kernel.encode()).hexdigest())

def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True, **kwargs)

for compiler, cxx in [('gcc', 'g++'), ('clang', '/usr/bin/clang++')]:
    manifest['compiler_versions'][compiler] = subprocess.check_output([cxx, '--version'], text=True).splitlines()[0]
    folder = output / compiler
    folder.mkdir(exist_ok=True)
    common = []
    for name in ['NativePixelClusterNN', 'PixelClusterNNFactory']:
        obj = folder / (name + '.o')
        run([cxx, *flags, '-DSICLUSTERIZATION_NATIVE_NN_HAVE_AVX2', '-c', package / f'src/{name}.cxx', '-o', obj])
        common.append(obj)
    for variant in variants:
        target = folder / variant
        target.mkdir(exist_ok=True)
        for name in ['NativePixelClusterNNBaseline.cxx', 'NativePixelClusterNNAvx2.cxx', 'NativePixelClusterNNConstants.h']:
            shutil.copyfile(package / 'src' / name, target / name)
        (target / 'NativePixelClusterNNKernel.icc').write_text(variants[variant])
        objects = list(common)
        for isa in ['Baseline', 'Avx2']:
            extra = ['-fvisibility=hidden', '-fvisibility-inlines-hidden', '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))']
            if isa == 'Avx2':
                extra += ['-mavx2', '-mfma', '-DEIGEN_MAX_ALIGN_BYTES=16']
            obj = target / (isa + '.o')
            run([cxx, *flags, *extra, '-c', target / f'NativePixelClusterNN{isa}.cxx', '-o', obj])
            objects.append(obj)
        run([cxx, '-shared', *objects, *shared, '-o', target / 'libNNUnroll.so'])
    run([cxx, *flags, here / 'interface_bench.cxx', '-L' + str(folder / reference), '-lNNUnroll', *shared,
         '-Wl,-rpath,' + str(folder / reference), '-o', folder / 'bench'])
    print(compiler, 'built', len(variants), 'variants', flush=True)
(output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')

def environment(compiler, variant, mode):
    env = os.environ.copy()
    for key in ['LD_PRELOAD', 'NATIVE_NN_FORCE_SSE', 'NATIVE_NN_FORCE_ONNX']:
        env.pop(key, None)
    env['LD_LIBRARY_PATH'] = str(output / compiler / variant) + ':' + env.get('LD_LIBRARY_PATH', '')
    env['NATIVE_NN_REPEATS'] = '5'
    if mode == 'sse':
        env['NATIVE_NN_FORCE_SSE'] = '1'
    return env

checks = {}
for compiler in ['gcc', 'clang']:
    checks[compiler] = {}
    for mode in ['auto', 'sse']:
        for variant in variants:
            dump = output / compiler / variant / (mode + '.bin')
            run(['taskset', '-c', '16', output / compiler / 'bench', 'dump', inputs, '100000', dump],
                env=environment(compiler, variant, mode))
        baseline = (output / compiler / reference / (mode + '.bin')).read_bytes()
        assert len(baseline) == 100000 * 33 * 4
        for variant in variants:
            assert (output / compiler / variant / (mode + '.bin')).read_bytes() == baseline, (compiler, mode, variant)
        checks[compiler][mode] = dict(inputs=100000, heads=4, bit_identical=True)
    print(compiler, '100k-input numerical comparison passed', flush=True)

rows = []
with (output / 'timing.jsonl').open('w') as log:
    for cycle in range(7):
        for compiler in ['gcc', 'clang']:
            for mode in ['auto', 'sse']:
                order = list(variants) if cycle % 2 == 0 else list(reversed(variants))
                for variant in order:
                    result = subprocess.check_output(['taskset', '-c', '16', str(output / compiler / 'bench'),
                                                      'time', str(inputs), '100000', 'unused'],
                                                     env=environment(compiler, variant, mode), text=True)
                    row = dict(cycle=cycle + 1, compiler=compiler, mode=mode, variant=variant, **json.loads(result))
                    rows.append(row); log.write(json.dumps(row) + '\n'); log.flush()
        print('cycle', cycle + 1, 'complete', flush=True)
summary = {}
for compiler in ['gcc', 'clang']:
    summary[compiler] = {}
    for mode in ['auto', 'sse']:
        if dense_review:
            baseline = [r['us'] for r in rows if (r['compiler'], r['mode'], r['variant']) == (compiler, mode, reference)]
            summary[compiler][mode] = {}
            for variant in variants:
                times = [r['us'] for r in rows if (r['compiler'], r['mode'], r['variant']) == (compiler, mode, variant)]
                changes = [100 * (b / a - 1) for a, b in zip(baseline, times)]
                summary[compiler][mode][variant] = dict(mean_us=statistics.mean(times), sd_us=statistics.stdev(times),
                                                       change_pct=statistics.mean(changes), paired_sd_pct=statistics.stdev(changes))
        else:
            plain = [r['us'] for r in rows if (r['compiler'], r['mode'], r['variant']) == (compiler, mode, 'plain')]
            unroll = [r['us'] for r in rows if (r['compiler'], r['mode'], r['variant']) == (compiler, mode, 'unroll')]
            changes = [100 * (b / a - 1) for a, b in zip(plain, unroll)]
            summary[compiler][mode] = dict(plain_us=statistics.mean(plain), plain_sd=statistics.stdev(plain),
                                           unroll_us=statistics.mean(unroll), unroll_sd=statistics.stdev(unroll),
                                           unroll_change_pct=statistics.mean(changes), paired_sd_pct=statistics.stdev(changes))
result = dict(numerics=checks, timing=summary)
(output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2), flush=True)
