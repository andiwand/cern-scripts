#!/usr/bin/env python3
"""Supplementary compiler-target check, without replacing the main binaries."""
import argparse,hashlib,json,os,statistics,subprocess,time
from pathlib import Path
S=Path(__file__).resolve().parent
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
V=R/'vectorization';V.mkdir(exist_ok=True)
p=argparse.ArgumentParser();p.add_argument('--standalone',action='store_true',help='Run sequentially without the original pipeline status barrier');args=p.parse_args()
def stage():return json.loads((R/'status.json').read_text())['status']
# The physics driver waits at a barrier until this sequential comparison ends.
while not args.standalone and stage() not in ['physics_validation','ready_for_report_review']:time.sleep(5)
with (V/'build.log').open('w') as log:
    subprocess.run(['bash',str(S/'build_v2.sh')],stdout=log,stderr=subprocess.STDOUT,check=True)
with (V/'validation.log').open('w') as log:
    subprocess.run(['bash',str(S/'validate_v2.sh')],stdout=log,stderr=subprocess.STDOUT,check=True)
v=json.loads((V/'validation/validation.json').read_text())
assert all(x['finite'] and not x['argmax_changes'] and not x['elements_outside_1e-5_plus_1e-4_relative'] for x in v['backends'].values())
print('x86-64-v2 numerical validation passed',flush=True)
variants=[(target,b) for b in ['direct','direct_avx2','sofie_gemv'] for target in ['sse2','v2']]
for cycle in range(3):
    order=variants if cycle==0 else list(reversed(variants)) if cycle==1 else variants[2:]+variants[:2]
    for target,backend in order:
        for pressure in [0,1048576]:
            d=V/f'c{cycle+1}'/f'{target}-{backend}'/str(pressure);d.mkdir(parents=True,exist_ok=True)
            if (d/'complete.txt').exists():continue
            (d/'load.json').write_text(json.dumps({'time':time.time(),'load':os.getloadavg(),'cpu':16}))
            with (d/'result.json').open('w') as out,(d/'stderr.log').open('w') as err:
                subprocess.run(['taskset','-c','16','bash',str(S/'vector_one.sh'),target,backend,str(pressure)],stdout=out,stderr=err,check=True)
            (d/'complete.txt').write_text('ok\n')
            print(cycle+1,target,backend,pressure,'complete',flush=True)
summary={}
for target,backend in variants:
    key=f'{target}-{backend}';summary[key]={}
    for pressure in ['0','1048576']:
        means=[statistics.mean(json.loads(p.read_text())['cycle_us']) for p in sorted(V.glob(f'c*/{key}/{pressure}/result.json'))]
        assert len(means)==3
        summary[key][pressure]={'mean_us':statistics.mean(means),'sd_us':statistics.stdev(means),'cycle_us':means}
summary['libraries']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'build/libNNInferenceStudy.so',R/'build-x86-v2/libNNInferenceStudy.so']}
(V/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (V/'kernel-profile.jsonl').open('w') as out,(V/'kernel-profile.log').open('w') as err:
    subprocess.run(['taskset','-c','16','bash',str(S/'kernels.sh')],stdout=out,stderr=err,check=True)
(V/'complete.txt').write_text('ok\n')
print('Vectorization comparison complete',flush=True)
