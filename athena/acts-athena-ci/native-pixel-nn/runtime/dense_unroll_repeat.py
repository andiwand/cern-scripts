#!/usr/bin/env python3
"""Resolve wall-time noise in the dense-hint screen with thread CPU time."""
import json
import os
from pathlib import Path
import statistics
import subprocess

root = Path('/home/astefl/source/acts/acts-athena-ci')
output = root / 'run/native-pixel-nn/dense-unroll-review'
manifest = json.loads((output / 'manifest.json').read_text())
external = Path(os.environ['NN_STUDY_EXTERNALS'])
source = Path(__file__).with_name('interface_bench.cxx').read_text()
source = source.replace('int main(', '''auto threadNow() {
 timespec t;
 if(clock_gettime(CLOCK_THREAD_CPUTIME_ID, &t)) throw std::runtime_error("clock_gettime failed");
 return std::chrono::seconds(t.tv_sec) + std::chrono::nanoseconds(t.tv_nsec);
}
int main(''').replace('std::chrono::steady_clock::now()', 'threadNow()')
path = output / 'thread_bench.cxx'
path.write_text('#include <time.h>\n' + source)
binary = output / 'gcc/bench_cpu'
subprocess.run(['g++', *manifest['flags'], str(path), '-L' + str(output / 'gcc/both'), '-lNNUnroll',
                '-L' + str(external / 'lib'), '-lonnxruntime', '-Wl,-rpath,' + str(external / 'lib'),
                '-Wl,-rpath,' + str(output / 'gcc/both'), '-o', str(binary)], check=True)
rows = []
with (output / 'cpu-timing.jsonl').open('w') as log:
    for cycle in range(7):
        for mode in ['auto', 'sse']:
            for variant in (['both', 'none'] if cycle % 2 == 0 else ['none', 'both']):
                env = os.environ.copy()
                for key in ['LD_PRELOAD', 'NATIVE_NN_FORCE_SSE', 'NATIVE_NN_FORCE_ONNX']:
                    env.pop(key, None)
                env['LD_LIBRARY_PATH'] = str(output / 'gcc' / variant) + ':' + env.get('LD_LIBRARY_PATH', '')
                env['NATIVE_NN_REPEATS'] = '5'
                if mode == 'sse': env['NATIVE_NN_FORCE_SSE'] = '1'
                result = json.loads(subprocess.check_output(['taskset', '-c', '28', str(binary), 'time',
                    str(root / 'run/nn-inference/captured-inputs.bin'), '100000', 'unused'], env=env, text=True))
                row = dict(cycle=cycle + 1, mode=mode, variant=variant, **result)
                rows.append(row); log.write(json.dumps(row) + '\n'); log.flush()
        print('CPU-time cycle', cycle + 1, 'complete', flush=True)
summary = {}
for mode in ['auto', 'sse']:
    baseline = [r['us'] for r in rows if (r['mode'], r['variant']) == (mode, 'both')]
    removed = [r['us'] for r in rows if (r['mode'], r['variant']) == (mode, 'none')]
    changes = [100 * (b / a - 1) for a, b in zip(baseline, removed)]
    summary[mode] = dict(both_us=statistics.mean(baseline), both_sd=statistics.stdev(baseline),
                         none_us=statistics.mean(removed), none_sd=statistics.stdev(removed),
                         change_pct=statistics.mean(changes), paired_sd_pct=statistics.stdev(changes))
result = dict(compiler='GCC 15.2', clock='CLOCK_THREAD_CPUTIME_ID', core=28,
              sample='100k captured inputs x5 repeats; seven alternating pairs; number + selected position', timing=summary)
(output / 'cpu-summary.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2), flush=True)
