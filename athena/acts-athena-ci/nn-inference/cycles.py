#!/usr/bin/env python3
"""Sequential timing; separate physics-only jobs may run concurrently."""
import argparse,json,os,subprocess,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S=Path(__file__).resolve().parent
R=Path('/home/astefl/source/acts/acts-athena-ci/run/nn-inference')
INPUT='/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1'
BACKENDS=['original','ort_cached','ort_simple','direct','direct_avx2','sofie','sofie_gemv','lwtnn','lwtnn_double','direct_blocked']
p=argparse.ArgumentParser();p.add_argument('mode',choices=['isolated','integrated','physics']);p.add_argument('--cpu',type=int,default=16);p.add_argument('--cycles',type=int,default=3);p.add_argument('--events',type=int,default=20);a=p.parse_args()

def snapshot():
    def counts():
        result={}
        for line in Path('/proc/stat').read_text().splitlines():
            if not line.startswith('cpu'):continue
            name,*fields=line.split();x=list(map(int,fields[:8]));result[name]=(sum(x),x[3]+x[4])
        return result
    before=counts();time.sleep(1);after=counts()
    usage={name:1-(idle-before[name][1])/(total-before[name][0]) if total>before[name][0] else 0 for name,(total,idle) in after.items()}
    siblings=Path(f'/sys/devices/system/cpu/cpu{a.cpu}/topology/thread_siblings_list').read_text().strip()
    return {'time':time.time(),'load':os.getloadavg(),'busy_cores':os.cpu_count()*usage['cpu'],'cpu':a.cpu,'sibling_cpus':siblings,'per_cpu_usage':{name:usage[name] for name in ['cpu'+x for x in siblings.split(',')]}}

def reconstruction(backend,cycle):
    d=R/a.mode/f'c{cycle+1}'/backend
    if (d/'complete.txt').exists():return
    d.mkdir(parents=True,exist_ok=True)
    (d/'load-start.json').write_text(json.dumps(snapshot()))
    command=['bash',str(S/'run.sh'),str(d),backend,str(a.events),INPUT,'4' if a.mode=='physics' else '0']
    if a.mode=='integrated':command=['taskset','-c',str(a.cpu)]+command
    if not (d/'exit-code.txt').exists():
        with (d/'driver.log').open('w') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert (d/'exit-code.txt').read_text().strip()=='0',d
    if not (d/'outcomes.txt.gz').exists():
        with (d/'extract.log').open('w') as log:subprocess.run(['bash',str(S/'extract.sh'),str(d),str(a.events)],stdout=log,stderr=subprocess.STDOUT,check=True)
    (d/'load-end.json').write_text(json.dumps(snapshot()))
    (d/'complete.txt').write_text('ok\n')
    print(a.mode,cycle+1,backend,'complete',flush=True)

if a.mode=='physics':
    # Reserve a sequential slot after the first reconstruction cycle for the
    # requested ISA/kernel checks; avoid overlapping our own timing workloads.
    deadline=time.monotonic()+3600
    while not (R/'vectorization/complete.txt').exists():
        if time.monotonic()>deadline:raise RuntimeError('Vectorization checks did not finish')
        time.sleep(5)
    # These results are never used as performance measurements.
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(reconstruction,b,0) for b in BACKENDS]
        for future in futures:future.result()
    raise SystemExit(0)

if a.mode=='integrated' and a.cycles>1:
    deadline=time.monotonic()+3600
    while not (R/'blocked/isolated-complete.txt').exists():
        if time.monotonic()>deadline:raise RuntimeError('Blocked SSE validation did not finish')
        time.sleep(5)

for cycle in range(a.cycles if a.mode!='physics' else 1):
    order=BACKENDS if cycle%3==0 else list(reversed(BACKENDS)) if cycle%3==1 else BACKENDS[4:]+BACKENDS[:4]
    for backend in order:
        if a.mode=='isolated':
            for pressure in [0,1024*1024]:
                d=R/'isolated'/f'c{cycle+1}'/backend/str(pressure);d.mkdir(parents=True,exist_ok=True)
                if (d/'complete.txt').exists():continue
                (d/'load-start.json').write_text(json.dumps(snapshot()))
                command=['taskset','-c',str(a.cpu),'bash',str(S/'time_one.sh'),backend,str(pressure)]
                with (d/'result.json').open('w') as out,(d/'stderr.log').open('w') as err:
                    subprocess.run(command,stdout=out,stderr=err,check=True)
                (d/'load-end.json').write_text(json.dumps(snapshot()))
                (d/'complete.txt').write_text('ok\n')
                print(a.mode,cycle+1,backend,pressure,'complete',flush=True)
        else:
            reconstruction(backend,cycle)

if a.mode=='isolated' and len(list((R/'isolated').glob('c*/*/*/complete.txt')))==60:
    (R/'blocked').mkdir(exist_ok=True)
    (R/'blocked/isolated-complete.txt').write_text('ok\n')
