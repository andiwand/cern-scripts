#!/usr/bin/env python3
"""Alternate standalone inference measurements on one CPU; no reconstruction."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess

ROOT = Path('/home/astefl/source/acts/acts-athena-ci/run')
OUT = ROOT / 'native-pixel-nn/cxxutils'
INPUT = ROOT / 'nn-inference/captured-inputs.bin'
parser = argparse.ArgumentParser()
parser.add_argument('stage', choices=['screen', 'final'])
args = parser.parse_args()
configurations = {}
for compiler in ['gcc', 'clang']:
    rows = [(f'eigen_{isa}', f'bench_eigen_{isa}', False) for isa in ['sse', 'avx2']]
    rows += [(f'shared_{isa}', f'bench_shared_{isa}', False) for isa in ['sse', 'avx2']]
    if args.stage == 'screen':
        for blocks in [1, 2, 4, 8]:
            rows += [(f'vec_b{blocks}_{isa}', f'bench_b{blocks}', isa == 'sse') for isa in ['sse', 'avx2']]
    else:
        selected = json.loads((OUT / 'selected.json').read_text())[compiler]
        for isa in ['sse', 'avx2']:
            blocks = selected[isa]
            rows.append((f'vec_b{blocks}_{isa}', 'bench_selected', isa == 'sse'))
            rows.append((f'direct_{isa}', f'bench_direct_{isa}', False))
    configurations[compiler] = rows

results = []
cycles = 3 if args.stage == 'screen' else 6
with (OUT / (args.stage + '-timing.jsonl')).open('w') as log:
    for cycle in range(cycles):
        compilers = ['gcc', 'clang'] if cycle % 2 == 0 else ['clang', 'gcc']
        for compiler in compilers:
            order = configurations[compiler]
            order = order[cycle % len(order):] + order[:cycle % len(order)]
            if cycle % 2: order = order[::-1]
            for label, binary, force_sse in order:
                env = os.environ.copy()
                env.pop('NATIVE_NN_FORCE_SSE', None)
                if force_sse: env['NATIVE_NN_FORCE_SSE'] = '1'
                env['NATIVE_NN_REPEATS'] = '2' if args.stage == 'screen' else '5'
                start_load = os.getloadavg()
                output = subprocess.check_output(['taskset', '-c', '16', str(OUT / compiler / binary),
                    'time', str(INPUT), '100000', 'unused'], env=env, text=True)
                row = dict(compiler=compiler, cycle=cycle + 1, label=label, **json.loads(output),
                           load_start=start_load, load_end=os.getloadavg())
                results.append(row)
                log.write(json.dumps(row) + '\n'); log.flush()
            print(f'{args.stage}: cycle {cycle + 1}/{cycles}, {compiler}', flush=True)

summary = {}
for compiler, configurations in configurations.items():
    summary[compiler] = {}
    for label, _, _ in configurations:
        values = [r['us'] for r in results if r['compiler'] == compiler and r['label'] == label]
        summary[compiler][label] = dict(mean_us=statistics.mean(values), sd_us=statistics.stdev(values), cycles=len(values))
(OUT / (args.stage + '-summary.json')).write_text(json.dumps(summary, indent=2) + '\n')
if args.stage == 'screen':
    selected = {compiler: {isa: min([1, 2, 4, 8], key=lambda blocks:
        summary[compiler][f'vec_b{blocks}_{isa}']['mean_us']) for isa in ['sse', 'avx2']} for compiler in summary}
    (OUT / 'selected.json').write_text(json.dumps(selected, indent=2) + '\n')
print(json.dumps(summary, indent=2))
