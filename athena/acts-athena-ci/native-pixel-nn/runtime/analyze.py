#!/usr/bin/env python3
"""Summarize completed final-candidate jobs and check their provenance."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

root = Path('/home/astefl/source/acts/acts-athena-ci')
out = Path(sys.argv[1]) if len(sys.argv)>1 else root/'run/native-pixel-nn/runtime-mr'
scripts = Path(__file__).resolve().parents[1]
for command in [('summarize.py', str(out)), ('compare_records.py', 'Native', str(out))]:
    subprocess.run(['python3', str(scripts/command[0]), *command[1:]], check=True)

def counters(directory):
    lines = (directory/'log.RAWtoALL').read_text().splitlines()
    lines = [re.sub(r'^\d\d:\d\d:\d\d ', '', line) for line in lines]
    return [line for line in lines if re.search(r'^\| |Number of truth particles with hits|Space Point Formation statistics|RDO truth stat', line)]

report = {'jobs': {}, 'smoke': {}}
reference = root/'run/native-pixel-nn/runtime-mr'
reference_checks = json.loads((reference/'job-checks.json').read_text()) if out != reference else None
if reference_checks:
    changed = subprocess.check_output(['git', '-C', str(root/'athena-native-pixel-nn'), 'diff', '--name-only', reference_checks['source_commit']], text=True).splitlines()
    assert set(changed) == {
        'InnerDetector/InDetRecTools/SiClusterizationTool/src/NativePixelClusterNNKernel.icc',
        'InnerDetector/InDetRecTools/SiClusterizationTool/doc/NativePixelClusterNN.md',
    }, 'Reusing ONNX physics requires an unchanged ONNX path'
paths = [out/'physics'/backend for backend in ['OnnxRuntime', 'Native']]
paths += [out/'timing'/f'c{cycle}'/backend for cycle in range(1, 4) for backend in ['OnnxRuntime', 'Native']]
paths += [out/stage/backend for stage in ['smoke-pre', 'smoke-default-threshold'] for backend in ['OnnxRuntime', 'Native']]
hashes = {}
for path in paths:
    reused = path.is_symlink()
    if reused:
        assert path.name == 'OnnxRuntime' and path.resolve() == (reference/path.relative_to(out)).resolve()
    assert (path/'exit-code.txt').read_text().strip() == '0', path
    assert 'NATIVE_NN_VALIDATION' in (path/'log.RAWtoALL').read_text(), path
    for line in (path/'libraries.txt').read_text().splitlines():
        digest, library = line.split(maxsplit=1)
        if library not in hashes:
            hashes[library] = hashlib.sha256(Path(library).read_bytes()).hexdigest()
        expected = reference_checks['unchanged_library_sha256'][library] if reused else hashes[library]
        assert expected == digest, (path, library)
    report['jobs'][str(path.relative_to(out))] = {
        'exit_code': 0,
        'start_utc': (path/'start.txt').read_text().strip(),
        'finish_utc': (path/'finish.txt').read_text().strip(),
        'reused_unchanged_onnx_reference': reused,
    }
for stage in ['smoke-pre', 'smoke-default-threshold']:
    a, b = (counters(out/stage/backend) for backend in ['OnnxRuntime', 'Native'])
    assert len(a) > 100 and a == b, stage
    report['smoke'][stage] = {'counter_rows': len(a), 'equal': True}
report['unchanged_library_sha256'] = hashes
if reference_checks:
    report['onnx_reference_source_commit'] = reference_checks['source_commit']
    report['onnx_reference_library_sha256'] = reference_checks['unchanged_library_sha256']
report['source_commit'] = subprocess.check_output(['git', '-C', str(root/'athena-native-pixel-nn'), 'rev-parse', 'HEAD'], text=True).strip()
assert report['source_commit'] == (out/'source-commit.txt').read_text().strip()
assert not subprocess.check_output(['git', '-C', str(root/'athena-native-pixel-nn'), 'status', '--porcelain'], text=True)
summary = json.loads((out/'summary.json').read_text())
assert all(row['events'] == 100 for row in summary['physics'].values())
assert all(len(rows) == 3 for rows in summary['timing'].values())
(out/'job-checks.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
