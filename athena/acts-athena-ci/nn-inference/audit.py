#!/usr/bin/env python3
"""Check study provenance and completeness before reporting results."""
import gzip
import hashlib
import json
from pathlib import Path

R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
BACKENDS = ['original', 'ort_cached', 'ort_simple', 'direct', 'direct_avx2',
            'sofie', 'sofie_gemv', 'lwtnn', 'lwtnn_double', 'direct_blocked']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

libraries = [R/'build/libNNInferenceStudy.so', R.parents[1]/
             'athena-build-nn-inference/x86_64-el9-gcc15-opt/lib/libActsTrackReconstruction.so']
libraries.append(R/'build-blocked/libNNInferenceStudy.so')
hashes = {str(path): sha(path) for path in libraries}
checked = []
fpe_warnings = {}
timing_records = {}
load_checks = {}
for sample, cycles, events in [('integrated', 3, 20), ('physics', 1, 100)]:
    for cycle in range(1, cycles+1):
        for backend in BACKENDS:
            run = R/sample/f'c{cycle}'/backend
            assert (run/'complete.txt').exists(), run
            assert (run/'exit-code.txt').read_text().strip() == '0', run
            assert (run/'backend.txt').read_text().strip() == backend, run
            for line in (run/'libraries.txt').read_text().splitlines():
                digest, path = line.split(maxsplit=1)
                assert hashes[path] == digest, (run, path)
            with gzip.open(run/'outcomes.txt.gz', 'rt') as stream:
                records = sorted(line.rstrip() for line in stream)
            count = sum(line.startswith('E ') for line in records)
            assert count == events, (run, count)
            if sample == 'integrated':
                start = json.loads((run/'load-start.json').read_text())['load'][0]
                end = json.loads((run/'load-end.json').read_text())['load'][0]
                assert max(start, end) < 20, (run, 'Overloaded timing endpoints')
                monitor = run/'load-monitor.json'
                peak = max(row['load'][0] for row in json.loads(monitor.read_text())) if monitor.exists() else None
                assert peak is None or peak < 20, (run, 'Overloaded timing interval')
                load_checks[str(run)] = {'start': start, 'end': end, 'monitored_peak': peak}
                digest = hashlib.sha256('\n'.join(records).encode()).hexdigest()
                if backend in timing_records:
                    assert digest == timing_records[backend], (run, 'Timing workload changed')
                timing_records[backend] = digest
            warnings = [line.split('WARNING', 1)[1].strip()
                        for line in (run/'log.RAWtoALL').read_text().splitlines()
                        if 'FPEAuditor' in line and 'WARNING' in line]
            fpe_warnings[str(run)] = warnings
            checked.append(str(run))
assert len(list((R/'isolated').glob('c*/*/*/complete.txt'))) == 60
for source in ['validation-real-athena', 'blocked/validation', 'vectorization/validation']:
    validation = json.loads((R/source/'validation.json').read_text())
    assert validation['inputs'] == 100000
    for backend, row in validation['backends'].items():
        assert row['finite'] and row['argmax_changes'] == 0, (source, backend)
        assert row['elements_outside_1e-5_plus_1e-4_relative'] == 0, (source, backend)
        assert row['max_relative_precision_error_selected_model'] < 1e-4, (source, backend)
assert sha(R/'blocked/validation/direct_blocked.bin') == sha(R/'validation-real-athena/direct.bin')
for backend in ['direct', 'direct_avx2', 'sofie_gemv']:
    assert sha(R/'vectorization/validation'/f'{backend}.bin') == sha(R/'validation-real-athena'/f'{backend}.bin')
assert not any(fpe_warnings.values()), fpe_warnings
reference_runs = []
reference_summary = R/'uncalibrated-reference/summary.json'
if reference_summary.exists():
    reference = json.loads(reference_summary.read_text())
    assert reference['complete_pairs'] == 3
    for mode, rows in reference['runs'].items():
        assert len(rows) == 3
        assert all(row['physics'] == rows[0]['physics'] and row['tracking_counters'] == rows[0]['tracking_counters'] for row in rows)
        for row in rows:
            run = Path(row['path'])
            assert (run/'complete.txt').exists() and (run/'exit-code.txt').read_text().strip() == '0'
            assert max(x['load'][0] for x in json.loads((run/'load-monitor.json').read_text())) < 20
            for line in (run/'libraries.txt').read_text().splitlines():
                digest, path = line.split(maxsplit=1)
                assert hashes[path] == digest, run
            reference_runs.append(str(run))
result = {'library_hashes': hashes, 'checked_runs': checked,
          'isolated_processes': 60, 'numerical_inputs': 100000,
          'blocked_outputs_identical_to_direct': True,
          'x86_v2_outputs_identical_to_sse2_build': True,
          'per_backend_timing_outcomes_identical_across_cycles': timing_records,
          'load_checks': load_checks, 'uncalibrated_reference_runs': reference_runs,
          'fpe_warnings': fpe_warnings}
(R/'artifact-audit.json').write_text(json.dumps(result, indent=2)+'\n')
print('Validated', len(checked), 'backend reconstruction jobs,', len(reference_runs), 'reference jobs and 60 standalone processes')
