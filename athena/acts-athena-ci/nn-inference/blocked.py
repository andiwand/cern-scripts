#!/usr/bin/env python3
"""Add the register-blocked SSE experiment without replacing reference binaries."""
import argparse,json,os,statistics,subprocess,time
from pathlib import Path
S=Path(__file__).resolve().parent
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
B=R/'blocked';B.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--standalone',action='store_true',help='Run sequentially without the original pipeline status barrier');args=p.parse_args()
INPUT='/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1'
for name in ['build_blocked','validate_blocked']:
    with (B/(name+'.log')).open('w') as log:
        subprocess.run(['bash',str(S/(name+'.sh'))],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Blocked SSE matches all outputs of direct SSE bit for bit on 100000 inputs',flush=True)
run=R/'physics/c1/direct_blocked';run.mkdir(parents=True,exist_ok=True)
with (run/'driver.log').open('w') as log:
    subprocess.run(['bash',str(S/'run.sh'),str(run),'direct_blocked','100',INPUT,'4'],stdout=log,stderr=subprocess.STDOUT,check=True)
with (run/'extract.log').open('w') as log:
    subprocess.run(['bash',str(S/'extract.sh'),str(run),'100'],stdout=log,stderr=subprocess.STDOUT,check=True)
(run/'complete.txt').write_text('ok\n')
print('Blocked SSE 100-event reconstruction complete',flush=True)
while not args.standalone and json.loads((R/'status.json').read_text())['status']!='integrated_remaining_cycles':time.sleep(5)
paired={}
for cycle in range(3):
    order=['direct','direct_blocked','sofie_gemv'] if cycle!=1 else ['sofie_gemv','direct_blocked','direct']
    for backend in order:
        for pressure in [0,1048576]:
            d=(R/'isolated' if backend=='direct_blocked' else B/'paired')/f'c{cycle+1}'/backend/str(pressure)
            d.mkdir(parents=True,exist_ok=True)
            (d/'load-start.json').write_text(json.dumps({'time':time.time(),'load':os.getloadavg(),'cpu':16}))
            with (d/'result.json').open('w') as out,(d/'stderr.log').open('w') as err:
                subprocess.run(['taskset','-c','16','bash',str(S/'time_one.sh'),backend,str(pressure)],stdout=out,stderr=err,check=True)
            (d/'complete.txt').write_text('ok\n')
            value=json.loads((d/'result.json').read_text())
            paired.setdefault(backend,{}).setdefault(str(pressure),[]).append(statistics.mean(value['cycle_us']))
            print(cycle+1,backend,pressure,'complete',flush=True)
(B/'paired-summary.json').write_text(json.dumps(paired,indent=2)+'\n')
(B/'isolated-complete.txt').write_text('ok\n')
print('Blocked SSE ready for serial reconstruction cycles',flush=True)
