#!/usr/bin/env python3
"""Accept timing only below the documented host-load ceiling; retain rejected runs."""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

S = Path(__file__).resolve().parent
R = Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
p = argparse.ArgumentParser()
p.add_argument('directory', type=Path)
p.add_argument('backend')
p.add_argument('--calibration', choices=['raw','post'])
a = p.parse_args()
run = a.directory.resolve()
assert run.is_relative_to(R), run
input_file = R.parent/'edge-holes/input/RDO.39626672._000001.pool.root.1'
while not (run/'complete.txt').exists():
    subprocess.run(['python3', str(S/'wait_quiet.py')], check=True)
    run.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    if a.calibration:
        env['NN_REFERENCE_CALIBRATION'] = a.calibration
    script = 'run_reference.sh' if a.calibration else 'run.sh'
    start = {'time': time.time(), 'load': os.getloadavg(), 'cpu': 16}
    (run/'load-start.json').write_text(json.dumps(start))
    samples = [start]
    with (run/'driver.log').open('w') as log:
        process = subprocess.Popen(['taskset','-c','16','bash',str(S/script),str(run),
                                    a.backend,'20',str(input_file),'0'],
                                   env=env, stdout=log, stderr=subprocess.STDOUT)
        while True:
            try:
                code = process.wait(timeout=10)
                break
            except subprocess.TimeoutExpired:
                samples.append({'time': time.time(), 'load': os.getloadavg()})
    end = {'time': time.time(), 'load': os.getloadavg(), 'cpu': 16}
    samples.append(end)
    (run/'load-end.json').write_text(json.dumps(end))
    (run/'load-monitor.json').write_text(json.dumps(samples, indent=2)+'\n')
    assert code == 0, (run, code)
    peak = max(row['load'][0] for row in samples)
    if peak >= 20:
        archive = R/'high-load-runs/retries'/str(int(time.time()))/run.relative_to(R)
        archive.parent.mkdir(parents=True, exist_ok=True)
        run.rename(archive)
        path = R/'timing-exclusions.json'
        data = json.loads(path.read_text())
        data['runs'].append({'original':str(run),'archive':str(archive),'peak_load':peak,
                             'reason':'Host load exceeded 20 during reconstruction.'})
        path.write_text(json.dumps(data, indent=2)+'\n')
        print('Retained overloaded run for audit; waiting to repeat:', run, peak, flush=True)
        continue
    with (run/'extract.log').open('w') as log:
        subprocess.run(['bash',str(S/'extract.sh'),str(run),'20'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    (run/'complete.txt').write_text('ok\n')
    print('Accepted timing:',run,'peak load',round(peak,2),flush=True)
