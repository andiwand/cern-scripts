#!/usr/bin/env python3
"""Paired measurements before/after the MR review, with immutable old libraries."""
import json, os, statistics, subprocess
from pathlib import Path
root = Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/mr-review')
input_file = root.parents[1]/'nn-inference/captured-inputs.bin'
rows = []
with (root/'standalone/review-timing.jsonl').open('w') as log:
    for cycle in range(6):
        for compiler in ('gcc', 'clang'):
            for mode in ('auto', 'sse'):
                for version in (('old', 'new') if cycle % 2 == 0 else ('new', 'old')):
                    env = os.environ.copy()
                    env['NATIVE_NN_REPEATS'] = '5'
                    env.pop('NATIVE_NN_FORCE_SSE', None)
                    if mode == 'sse': env['NATIVE_NN_FORCE_SSE'] = '1'
                    directory = root/'old' if version == 'old' else root/'standalone'
                    if version == 'old':
                        lib = directory if compiler == 'gcc' else directory/'clang'
                        env['LD_LIBRARY_PATH'] = str(lib)+':'+env.get('LD_LIBRARY_PATH', '')
                        # Older clients use DT_RPATH, which precedes LD_LIBRARY_PATH.
                        library = 'libSiClusterizationToolLib.so' if compiler == 'gcc' else 'libNativeRuntime.so'
                        env['LD_PRELOAD'] = str(lib/library)
                    result = subprocess.check_output(['taskset', '-c', '16',
                        str(directory/f'bench_{compiler}'), 'time', str(input_file), '100000', 'unused'],
                        text=True, env=env)
                    row = dict(cycle=cycle+1, compiler=compiler, mode=mode, version=version, **json.loads(result))
                    rows.append(row); log.write(json.dumps(row)+'\n'); log.flush()
        print('cycle', cycle+1, flush=True)
summary = {}
for compiler in ('gcc', 'clang'):
    summary[compiler] = {}
    for mode in ('auto', 'sse'):
        old = [r['us'] for r in rows if (r['compiler'],r['mode'],r['version']) == (compiler,mode,'old')]
        new = [r['us'] for r in rows if (r['compiler'],r['mode'],r['version']) == (compiler,mode,'new')]
        delta = [100*(b/a-1) for a,b in zip(old,new)]
        summary[compiler][mode] = dict(old_us=statistics.mean(old), new_us=statistics.mean(new),
            new_sd_us=statistics.stdev(new), paired_change_percent=statistics.mean(delta),
            paired_change_sd_percent=statistics.stdev(delta))
(root/'standalone/review-timing.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
