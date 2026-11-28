#!/usr/bin/env python3
"""Summarize a finished campaign and check job provenance.

analyze.py OUT [--events 100] [--timing-events 20] [--cycles 3] [--no-fallback]
Runs summarize.py and compare_records.py, then checks every job exited 0 with the
validation config, all jobs used the same library hashes (no symlinked reuse), the
smoke tracking counters agree between backends, the fallback job logged the native
rejection, and the source tree is clean at the recorded commit. Writes OUT/job-checks.json.
"""
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
source = root/'athena-native-pixel-nn'
scripts = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('out', type=Path)
parser.add_argument('--events', type=int, default=100)
parser.add_argument('--timing-events', type=int, default=20)
parser.add_argument('--cycles', type=int, default=3)
parser.add_argument('--no-fallback', action='store_true')
args = parser.parse_args()
out = args.out
subprocess.run(['python3', str(scripts/'summarize.py'), str(out), '--timing-events', str(args.timing_events)], check=True)
subprocess.run(['python3', str(scripts/'compare_records.py'), 'Native', str(out)], check=True)

def counters(directory):
    lines = (directory/'log.RAWtoALL').read_text().splitlines()
    lines = [re.sub(r'^\d\d:\d\d:\d\d ', '', line) for line in lines]
    return [line for line in lines if re.search(r'^\| |Number of truth particles with hits|Space Point Formation statistics|RDO truth stat', line)]

report = {'jobs': {}, 'smoke': {}}
paths = [out/'physics'/backend for backend in ['OnnxRuntime', 'Native']]
paths += [out/'timing'/f'c{cycle}'/backend for cycle in range(1, args.cycles+1) for backend in ['OnnxRuntime', 'Native']]
if not args.no_fallback:
    paths += [out/'smoke-fallback/Native']
paths += [out/stage/backend for stage in ['smoke-pre', 'smoke-default-threshold'] for backend in ['OnnxRuntime', 'Native']]
hashes = {}
for path in paths:
    assert not path.is_symlink(), 'All jobs must use the current build'
    assert (path/'exit-code.txt').read_text().strip() == '0', path
    assert 'NATIVE_NN_VALIDATION' in (path/'log.RAWtoALL').read_text(), path
    for line in (path/'libraries.txt').read_text().splitlines():
        digest, library = line.split(maxsplit=1)
        if library not in hashes:
            hashes[library] = hashlib.sha256(Path(library).read_bytes()).hexdigest()
        assert hashes[library] == digest, (path, library)
    report['jobs'][str(path.relative_to(out))] = {
        'exit_code': 0,
        'start_utc': (path/'start.txt').read_text().strip(),
        'finish_utc': (path/'finish.txt').read_text().strip(),
    }
for stage in ['smoke-pre', 'smoke-default-threshold']:
    a, b = (counters(out/stage/backend) for backend in ['OnnxRuntime', 'Native'])
    assert len(a) > 100 and a == b, stage
    report['smoke'][stage] = {'counter_rows': len(a), 'equal': True}
if not args.no_fallback:
    fallback_log = (out/'smoke-fallback/Native/log.RAWtoALL').read_text()
    assert 'Using ONNX Runtime for' in fallback_log and 'native construction failed:' in fallback_log
    report['smoke']['fallback'] = {'logged_native_rejection': True, 'exit_code': 0}
report['unchanged_library_sha256'] = hashes
report['source_commit'] = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
assert report['source_commit'] == (out/'source-commit.txt').read_text().strip()
assert not subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True)
summary = json.loads((out/'summary.json').read_text())
assert all(row['events'] == args.events for row in summary['physics'].values())
assert all(len(rows) == args.cycles for rows in summary['timing'].values())
(out/'job-checks.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
