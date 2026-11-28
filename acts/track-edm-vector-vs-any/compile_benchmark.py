"""Measure isolated release compilations without ccache or concurrent workloads."""
import json
import os
import resource
import shlex
import subprocess
import sys
import time
from pathlib import Path

# A fresh wrapper per command makes ru_maxrss specific to that compilation.
if '--single' in sys.argv:
    spec = json.load(sys.stdin)
    start = time.perf_counter()
    run = subprocess.run(spec['args'], cwd=spec['cwd'], capture_output=True, text=True)
    elapsed = time.perf_counter() - start
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    print(json.dumps(dict(returncode=run.returncode, stdout=run.stdout, stderr=run.stderr,
                         wall_s=elapsed, user_s=usage.ru_utime, system_s=usage.ru_stime,
                         rss_bytes=usage.ru_maxrss * (1 if sys.platform == 'darwin' else 1024))))
    sys.exit(0)

base = Path(os.environ.get('ACTS_EDM_EXPERIMENT_ROOT', '/private/tmp/acts-edm-2026-10-31'))
dest = base / 'results' / 'compile'
dest.mkdir(exist_ok=True)
records = []
orders = [['main', 'vector', 'any'], ['vector', 'any', 'main'], ['any', 'main', 'vector']]
for source in ['TrackFindingAlgorithmFunction.cpp', 'TrackFindingAlgorithm.cpp']:
    for block, order in enumerate(orders):
        for variant in order:
            entries = json.loads((base / f'build-{variant}/compile_commands.json').read_text())
            entry = next(e for e in entries if e['file'].endswith('/' + source))
            args = shlex.split(entry['command'])
            obj = dest / f'{variant}-{source}-{block}.o'
            args[args.index('-o') + 1] = str(obj)
            stem = dest / f'{variant}-{source}-{block}'
            Path(str(stem) + '.command.txt').write_text(shlex.join(args) + '\n')
            run = subprocess.run([sys.executable, __file__, '--single'],
                                 input=json.dumps(dict(args=args, cwd=entry['directory'])),
                                 capture_output=True, text=True, check=True)
            result = json.loads(run.stdout)
            Path(str(stem) + '.log').write_text(json.dumps(result, indent=2))
            if result['returncode']:
                raise SystemExit(result['stderr'])
            record = dict(variant=variant, source=source, block=block,
                          object_bytes=obj.stat().st_size,
                          **{k: result[k] for k in ['wall_s', 'user_s', 'system_s', 'rss_bytes']})
            records.append(record)
            print(record, flush=True)
            (dest / 'results.json').write_text(json.dumps(records, indent=2))
