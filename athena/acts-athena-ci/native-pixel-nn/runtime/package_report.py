#!/usr/bin/env python3
"""Archive compact evidence without replacing the earlier Eigen review."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
results = root/'run/native-pixel-nn'
current = results/'runtime-final'
target = Path('/home/astefl/notes/atlas/tsi/notebook/2026-11-24_native-pixel-nn-final-candidate/runtime-simd')
target.mkdir(parents=True, exist_ok=True)
files = {
    'summary.json': 'integration.json',
    'physics/record-comparison.json': 'track-comparison.json',
    'standalone/summary.json': 'isolated-timing.json',
    'standalone/timing.jsonl': 'isolated-cycles.jsonl',
    'standalone/ort-baseline.json': 'ort-baseline.json',
    'standalone/gcc/validation/validation.json': 'gcc-validation.json',
    'standalone/clang/validation/validation.json': 'clang-validation.json',
    'isa-audit.json': 'isa-audit.json',
    'job-checks.json': 'job-checks.json',
    'loc.json': 'loc.json',
    'tests-final-off.log': 'tests-off.log',
    'tests-final-on.log': 'tests-on.log',
    'on-restore-check.log': 'on-restore-check.log',
    'debug-audit/summary.json': 'debug-isa-audit.json',
    'release-equivalence.json': 'release-equivalence.json',
}
for source, destination in files.items():
    shutil.copyfile(current/source, target/destination)
for name in ['summary.json', 'clean-verification.json']:
    shutil.copyfile(results/'cxxutils/tuning'/name, target/('prototype-'+name))
for mode in ['auto', 'sse']:
    shutil.copyfile(results/'cxxutils/tuning/sanitizer'/mode/'test.log', target/('prototype-sanitizer-'+mode+'.log'))
source = root/'athena-native-pixel-nn'
def git(*args):
    return subprocess.check_output(['git', '-C', str(source), *args], text=True).strip()
base = '41da040949efeca5de0e5adbd84054868a5165c6'
paths = git('diff', '--name-only', base).splitlines()
review = {
    'generated_utc': datetime.now(timezone.utc).isoformat(),
    'source_branch': git('branch', '--show-current'),
    'source_commit': git('rev-parse', 'HEAD'),
    'scripts_commit': subprocess.check_output(['git', '-C', '/home/astefl/scripts', 'rev-parse', 'HEAD'], text=True).strip(),
    'base_commit': base,
    'source_clean': not git('status', '--porcelain'),
    'source_sha256': {path: hashlib.sha256((source/path).read_bytes()).hexdigest() for path in paths},
    'nightly': '2026-11-23T2100',
    'platform': 'x86_64-el9-gcc15-opt',
    'compiler': 'GCC 15.2; standalone Clang 20.1.8',
    'onnxruntime': '1.26', 'eigen': '3.4.1', 'acts': '48.5.0',
    'host': 'AMD Threadripper 3970X', 'timed_cpu': 16,
    'final_on_tests_also_force_baseline': True,
    'source_review': [
        'Loader dimensions, tensor ownership/transposition, transforms and failure paths checked.',
        'Native and ONNX clients share conditions; inference weights are immutable and scratch is per call.',
        'AVX2/FMA detection occurs once per model; no AVX in dispatcher, loader or baseline objects.',
        'Hidden ISA kernels and forced-inline Eigen expression helpers prevent ISA helper interposition/merging.',
        'Scalar C math calls and explicit maximum avoid shared C++ scalar helpers in debug builds.',
        'GCC/Clang O0 and O1+sanitizer objects contain no shared AVX-bearing scalar helpers; remaining helpers encode eight-float packet width.',
        'One shared kernel; excluded bias-first/dynamic-dimension/custom-exp experiments.',
    ],
    'limits': [
        '100 ttbar mu=200 events; numerical changes can change decisions on other samples.',
        'Full integration uses GCC automatic AVX2 dispatch; Clang and forced SSE are checked standalone.',
        'No non-AVX machine/emulator was available; forced SSE and instruction/symbol audits cover fallback here.',
        'Startup probes check compatibility of a supported architecture, not exhaustive graph equivalence.',
        'Sanitizer logs concern the selected clean prototype kernel, not the complete Athena process.',
        'Earlier review artifacts and prototype results retain their original scope; runtime-simd contains the integrated result.',
    ],
    'scripts': 'athena/acts-athena-ci/native-pixel-nn in https://github.com/andiwand/cern-scripts',
    'result_directory': str(current),
}
assert review['source_clean']
equivalence = json.loads((current/'release-equivalence.json').read_text())
assert equivalence['final_source_commit'] == review['source_commit']
review['measurement_basis'] = 'Final native physics, both serial timing sides and isolated timing are repeated after the debug-wrapper fix because GCC changed release instructions. The ONNX physics/smoke references are reused: only the unused native kernel changed on that path. Clang loaded release sections are identical except build ID.'
(target/'review.json').write_text(json.dumps(review, indent=2)+'\n')
print(target)
