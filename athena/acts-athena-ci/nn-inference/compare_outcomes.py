#!/usr/bin/env python3
"""Compare printed event, truth and reconstructed-track records without ordering."""
import gzip
import hashlib
import json
import re
import difflib
from pathlib import Path

R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
pairs = {
    'previous_SeedOnly_vs_current_ONNX': (
        R.parent/'seed-measurement-policy/full/post/SeedOnly/f01/outcomes.txt.gz',
        R/'physics/c1/original/outcomes.txt.gz'),
    'direct_SSE_vs_blocked_SSE': (
        R/'physics/c1/direct/outcomes.txt.gz',
        R/'physics/c1/direct_blocked/outcomes.txt.gz'),
}
result = {}
for label, paths in pairs.items():
    rows = []
    for path in paths:
        with gzip.open(path, 'rt') as stream:
            rows.append(sorted(line.rstrip() for line in stream))
    result[label] = {
        'paths': [str(path) for path in paths],
        'events': [sum(line.startswith('E ') for line in row) for row in rows],
        'records': [len(row) for row in rows],
        'sorted_record_sha256': [hashlib.sha256('\n'.join(row).encode()).hexdigest() for row in rows],
        'identical': rows[0] == rows[1],
        'scope': 'Printed R/T/E records; not binary trajectory equality',
    }
    assert result[label]['events'] == [100, 100], label
(R/'outcome-comparisons.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))

def counter_rows(path):
    rows = [re.sub(r'^\d\d:\d\d:\d\d ', '', line) for line in path.read_text().splitlines()]
    return [line for line in rows if re.search(
        r'^\| |Number of truth particles with hits|Space Point Formation statistics|RDO truth stat', line)]

reference = counter_rows(R/'physics/c1/original/log.RAWtoALL')
counters = {}
for run in sorted((R/'physics/c1').iterdir()):
    path = run/'log.RAWtoALL'
    if not path.exists():
        continue
    rows = counter_rows(path)
    counters[run.name] = {
        'identical': rows == reference,
        'rows': len(rows),
        'differences': list(difflib.unified_diff(reference, rows, fromfile='original', tofile=run.name)),
    }
(R/'tracking-counter-comparison.json').write_text(json.dumps(counters, indent=2)+'\n')
assert len(counters) == 10 and all(row['identical'] for row in counters.values())
print('All ten tracking-statistics tables agree with current ONNX.')
