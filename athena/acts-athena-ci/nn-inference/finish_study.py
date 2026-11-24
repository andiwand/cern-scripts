#!/usr/bin/env python3
"""Resume after the one launch-only failure, retaining all successful jobs."""
import json,subprocess,time
from pathlib import Path
S=Path(__file__).resolve().parent
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
backends=['original','ort_cached','ort_simple','direct','direct_avx2','sofie','sofie_gemv','lwtnn','lwtnn_double','direct_blocked']
deadline=time.monotonic()+3600
while True:
    ready=True
    for backend in backends:
        d=R/'physics/c1'/backend
        if not (d/'complete.txt').exists() or not (d/'outcomes.txt.gz').exists():ready=False;continue
        assert (d/'exit-code.txt').read_text().strip()=='0',d
    if ready:break
    if time.monotonic()>deadline:raise RuntimeError('Physics recovery did not finish')
    time.sleep(5)
while Path('/proc/380930/cmdline').exists():
    try:command=Path('/proc/380930/cmdline').read_bytes()
    except FileNotFoundError:break
    if b'/nn-inference/pipeline.py' not in command:break
    time.sleep(2)
subprocess.run(['python3',str(S/'summarize.py')],check=True)
p=R/'status.json';d=json.loads(p.read_text());d.update(status='integrated_remaining_cycles',backend_count=10,physics_completed=10,isolated_expected_runs=60,updated_epoch=time.time());p.write_text(json.dumps(d,indent=2)+'\n')
with (R/'integrated_remaining_cycles-driver.log').open('a') as log:
    subprocess.run(['python3',str(S/'cycles.py'),'integrated','--cycles','3','--events','20','--cpu','16'],stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run(['python3',str(S/'summarize.py')],check=True)
d=json.loads(p.read_text());d.update(status='ready_for_report_review',isolated_completed_runs=60,updated_epoch=time.time());p.write_text(json.dumps(d,indent=2)+'\n')
print('All reconstruction and isolated comparisons complete',flush=True)
