#!/usr/bin/env python3
"""Summarize compute-only evidence, keeping comparisons within the same run."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess

ROOT = Path('/home/astefl/source/acts/acts-athena-ci')
OUT = ROOT / 'run/native-pixel-nn/cxxutils'
HERE = Path(__file__).resolve().parent
rows = [json.loads(line) for line in (OUT / 'final-timing.jsonl').read_text().splitlines()]
timing = json.loads((OUT / 'final-summary.json').read_text())
selection = json.loads((OUT / 'selected.json').read_text())
comparisons = {}
numerical = {}
for compiler in ['gcc', 'clang']:
    samples = {(r['label'], r['cycle']):r['us'] for r in rows if r['compiler'] == compiler}
    comparisons[compiler] = {}
    for isa in ['sse', 'avx2']:
        label = f'vec_b{selection[compiler][isa]}_{isa}'
        for reference in [f'eigen_{isa}', f'shared_{isa}', f'direct_{isa}', 'eigen_sse']:
            delta = [100 * (samples[label, cycle] / samples[reference, cycle] - 1) for cycle in range(1, 7)]
            comparisons[compiler][label + '_vs_' + reference] = {
                'mean_percent':statistics.mean(delta), 'cycle_sd_percent':statistics.stdev(delta)}
    validation = json.loads((OUT / compiler / 'validation/validation.json').read_text())
    numerical[compiler] = {key: {metric:value[metric] for metric in [
        'finite', 'max_abs', 'max_scaled', 'argmax_changes',
        'elements_outside_1e-5_plus_1e-4_relative', 'max_relative_precision_error_selected_model']}
        for key, value in validation['backends'].items()}

sources = {str(path.relative_to(OUT)):hashlib.sha256(path.read_bytes()).hexdigest()
           for path in OUT.rglob('*') if path.is_file() and path.suffix in ['.cxx', '.icc', '.h'] and 'initial' not in path.parts}
result = {
    'scope':'Standalone inference only; no reconstruction or physics checks; Athena MR candidate unchanged.',
    'candidate_commit':subprocess.check_output(['git', '-C', str(ROOT / 'athena-native-pixel-nn'), 'rev-parse', 'HEAD'], text=True).strip(),
    'method':{'cpu':'Threadripper 3970X, CPU 16', 'compilers':['GCC 15.2', 'Clang 20.1.8'],
              'flags':'-O2 -DNDEBUG -std=c++23 -march=x86-64-v2; AVX2 kernels add -mavx2 -mfma; no -ffast-math',
              'work':'number plus multiplicity-selected position network; 100000 captured inputs, 5 repeats per measurement, 6 alternating cycles',
              'excludes':'model loading, startup comparison, cluster input preparation and reconstruction',
              'uncertainty':'Sample standard deviation over cycles, not error on the mean.'},
    'implementation':{'gemv':'CxxUtils::vec<float,4> / vec<float,8>, input-major weights, up to eight output accumulators; two GCC-unroll pragmas also supported by Clang.',
                      'activation':'Eigen SiLU compiled once for SSE, shared by both ISA kernels.',
                      'dispatch':'AVX2 AND FMA checked once per model; a predictable branch chooses the inference kernel. Harness can force SSE.',
                      'small_heads':'Unpadded scalar loops for 3/5/10/15 outputs; compiler may vectorize.',
                      'dense_nonblank_noncomment_lines':sum(bool(line.strip()) and not line.lstrip().startswith('//') for line in (HERE / 'Dense.icc').read_text().splitlines())},
    'selection':selection, 'timing':timing, 'paired_comparisons':comparisons, 'numerical':numerical,
    'isa_audit':json.loads((OUT / 'isa-audit.json').read_text()),
    'limitations':['Forced SSE and instruction inspection on an AVX2 host; no non-AVX hardware/emulator run.',
                   'No reconstruction or physics validation for this prototype.',
                   'The prototype retains SSE activation; it is not a fully AVX2-vectorized network.'],
    'generated_source_sha256':sources}
(OUT / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
for compiler in comparisons:
    print(compiler, json.dumps(comparisons[compiler], indent=2))
