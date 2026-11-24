#!/usr/bin/env python3
"""Compare the matched raw and blocked-SSE reconstruction costs."""
import gzip
import hashlib
import json
import re
import statistics as st
import tarfile
from pathlib import Path

R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
U = R/'uncalibrated-reference'
out = {'configuration': 'SeedOnly; primary-only raw versus all-charge/size NN post-calibration; blocked SSE; unchanged 7/10 sigma cuts and LRT',
       'runs': {'raw': [], 'post': []}, 'comparisons': {}}
for calibration in out['runs']:
    for run in sorted(U.glob(f'c*/{calibration}')):
        if not (run/'complete.txt').exists():
            continue
        assert (run/'exit-code.txt').read_text().strip() == '0', run
        assert (run/'calibration.txt').read_text().strip() == calibration, run
        assert 'runArgs.threads = 0' in (run/'runargs.RAWtoALL.py').read_text(), run
        for line in (run/'libraries.txt').read_text().splitlines():
            digest, path = line.split(maxsplit=1)
            assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, run
        with tarfile.open(run/'perfmonmt_RAWtoALL.json.tar.gz') as archive:
            data = json.load(archive.extractfile(archive.getmembers()[0]))
        components = data['componentLevel']['Execute']
        n = components['ActsTrackFindingAlg']['count']
        assert n == 19 and data['summary']['nEvents'] == 20, run
        log = (run/'log.RAWtoALL').read_text()
        policy = next(line for line in log.splitlines() if 'POLICY_CKF ActsTrackFindingAlg ' in line)
        assert 'SeedOnly' in policy and '[7.0] [10.0] [3]' in policy, policy
        assert ('SeedPolicyNN' in policy) == (calibration == 'post'), policy
        assert not any('FPEAuditor' in line and 'WARNING' in line for line in log.splitlines()), run
        table = log.split('INFO statistics:', 1)[1].split('INFO Ratios:', 1)[0]
        counters = {}
        for line in table.splitlines():
            fields = line.split('|')
            if len(fields) == 6 and fields[-2].strip().isdigit():
                counters[re.sub(r'\s+', ' ', fields[1]).strip()] = int(fields[-2])
        with gzip.open(run/'outcomes.txt.gz', 'rt') as stream:
            events = [list(map(int, line.split()[3:])) for line in stream if line.startswith('E ')]
        assert len(events) == 20, run
        physics = dict(zip(['truth','matched','duplicate_truth','reco','fakes','half'], map(sum, zip(*events))))
        row = {'path': str(run), 'cycle': run.parent.name, 'timed_events': n,
               'ckf_ms': components['ActsTrackFindingAlg']['cpuTime']/n,
               'control_ms': components['ActsPixelClusterizationAlg']['cpuTime']/n,
               'event_ms': data['summary']['snapshotLevel']['Execute']['dCPU']/n,
               'policy': policy, 'tracking_counters': counters, 'physics': physics}
        out['runs'][calibration].append(row)
raw = {row['cycle']: row for row in out['runs']['raw']}
paired = [row for row in out['runs']['post'] if row['cycle'] in raw]
out['complete_pairs'] = len(paired)
for field in ['ckf_ms', 'event_ms']:
    ratios = [row[field]/row['control_ms']/(raw[row['cycle']][field]/raw[row['cycle']]['control_ms']) for row in paired]
    if ratios:
        out['comparisons'][field] = {'normalized_ratio': st.mean(ratios),
            'sd_ratio': st.stdev(ratios) if len(ratios) > 1 else None, 'cycle_ratios': ratios}
out['means'] = {name: {field: st.mean(row[field] for row in rows) for field in ['ckf_ms','event_ms','control_ms']}
                for name, rows in out['runs'].items() if rows}
(U/'summary.json').write_text(json.dumps(out, indent=2)+'\n')
print('Raw/post pairs:', len(paired), 'CPU comparisons:', out['comparisons'], flush=True)
