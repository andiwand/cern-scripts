#!/usr/bin/env python3
"""Alternating, CPU-pinned timing of standalone bench binaries.

bench_time.py --case LABEL=BINARY[:ENV=V[,ENV=V]] [--case ...] --out DIR
              [--cycles 3] [--inputs 50000] [--repeats 3] [--cpu 16] [--input-file PATH]

Each cycle runs every case once (`taskset -c CPU BINARY time INPUTS N unused`),
reversing the order on every other cycle. NATIVE_NN_FORCE_SSE, NATIVE_NN_FORCE_ONNX
and LD_PRELOAD are cleared before applying a case's ENV; NATIVE_NN_REPEATS is set.
To time an older library with a newer client, set LD_PRELOAD (and LD_LIBRARY_PATH)
in the case. The first case is the baseline for paired per-cycle changes.
Writes DIR/timing.jsonl and DIR/timing.json. Run through bench_env.sh, on an idle
machine, with no build or reconstruction running.
"""
import argparse
import json
import os
import statistics
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--case', action='append', required=True, metavar='LABEL=BINARY[:ENV=V,...]')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--cycles', type=int, default=3)
parser.add_argument('--inputs', type=int, default=50000)
parser.add_argument('--repeats', type=int, default=3)
parser.add_argument('--cpu', default='16')
parser.add_argument('--input-file', type=Path,
                    default=Path(os.environ.get('NATIVE_NN_INPUTS') or
                                 Path(os.environ.get('NN_STUDY_ROOT', '/home/astefl/source/acts/acts-athena-ci/run/nn-inference'))/'captured-inputs.bin'))
args = parser.parse_args()

cases = {}
for spec in args.case:
    label, rest = spec.split('=', 1)
    binary, _, extra = rest.partition(':')
    cases[label] = (binary, dict(item.split('=', 1) for item in extra.split(',') if item))
labels = list(cases)
args.out.mkdir(parents=True, exist_ok=True)

def environment(extra):
    env = os.environ.copy()
    for key in ['NATIVE_NN_FORCE_SSE', 'NATIVE_NN_FORCE_ONNX', 'LD_PRELOAD']:
        env.pop(key, None)
    env['NATIVE_NN_REPEATS'] = str(args.repeats)
    for key, value in extra.items():
        if key == 'LD_LIBRARY_PATH':
            value = value + ':' + env.get('LD_LIBRARY_PATH', '')
        env[key] = value
    return env

rows = []
with (args.out/'timing.jsonl').open('w') as log:
    for cycle in range(args.cycles):
        for label in (labels if cycle % 2 == 0 else labels[::-1]):
            binary, extra = cases[label]
            output = subprocess.check_output(['taskset', '-c', args.cpu, binary, 'time', str(args.input_file),
                                              str(args.inputs), 'unused'], env=environment(extra), text=True)
            row = dict(cycle=cycle+1, label=label, **json.loads(output))
            rows.append(row); log.write(json.dumps(row)+'\n'); log.flush()
        print('cycle', cycle+1, 'complete', flush=True)

def sd(values):
    return statistics.stdev(values) if len(values) > 1 else None

baseline = [r['us'] for r in rows if r['label'] == labels[0]]
summary = {}
for label in labels:
    times = [r['us'] for r in rows if r['label'] == label]
    changes = [100*(b/a-1) for a, b in zip(baseline, times)]
    summary[label] = dict(mean_us=statistics.mean(times), sd_us=sd(times), cycles=len(times),
                          change_pct=statistics.mean(changes), paired_sd_pct=sd(changes))
result = dict(method=f'{args.cycles} alternating cycles, {args.inputs} captured inputs x{args.repeats} repeats, '
                     f'number + selected position, CPU {args.cpu}', baseline=labels[0],
              cases={label: dict(binary=cases[label][0], env=cases[label][1]) for label in labels}, timing=summary)
(args.out/'timing.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
