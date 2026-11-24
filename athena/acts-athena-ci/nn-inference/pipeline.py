#!/usr/bin/env python3
"""Finish full reconstruction comparisons after standalone timing completes."""
import json,subprocess,time
from pathlib import Path
S=Path(__file__).resolve().parent
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')

def state(stage):
    p=R/'status.json';d=json.loads(p.read_text());d['status']=stage;d['updated_epoch']=time.time();p.write_text(json.dumps(d,indent=2)+'\n')

deadline=time.monotonic()+3600
while len(list((R/'isolated').glob('c*/*/*/complete.txt')))<60:
    if time.monotonic()>deadline:raise RuntimeError('Standalone cycles did not finish within one hour')
    time.sleep(5)
subprocess.run(['python3',str(S/'summarize.py')],check=True)
state('calibration_cost_profile')
with (R/'profile-driver.log').open('w') as log:
    subprocess.run(['bash',str(S/'profile.sh')],stdout=log,stderr=subprocess.STDOUT,check=True)
for stage,args in [
    ('integrated_first_cycle',['integrated','--cycles','1','--events','20','--cpu','16']),
    ('physics_validation',['physics','--events','100']),
    ('integrated_remaining_cycles',['integrated','--cycles','3','--events','20','--cpu','16']),
]:
    state(stage)
    print(stage,'started',time.strftime('%FT%T%z'),flush=True)
    with (R/(stage+'-driver.log')).open('a') as log:
        subprocess.run(['python3',str(S/'cycles.py'),*args],stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run(['python3',str(S/'summarize.py')],check=True)
    print(stage,'complete',time.strftime('%FT%T%z'),flush=True)
state('ready_for_report_review')
