#!/usr/bin/env python3
import argparse,json,os,statistics,subprocess
from pathlib import Path
PARENT=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils')
OUT=PARENT/'tuning';INPUT=PARENT.parent.parent/'nn-inference/captured-inputs.bin'
p=argparse.ArgumentParser();p.add_argument('stage',choices=['screen','final']);args=p.parse_args()
config={}
for compiler in ['gcc','clang']:
    if args.stage=='screen':
        cases=os.environ.get('NATIVE_VEC_CASES','packet unroll flat heads bias').split()
        config[compiler]=[(f'{case}_{isa}',OUT/compiler/f'bench_{case}',isa=='sse') for case in cases for isa in ['sse','avx2']]
    else:
        config[compiler]=[(f'tuned_{isa}',OUT/compiler/'bench_tuned',isa=='sse') for isa in ['sse','avx2']]
    config[compiler]+=[(f'eigen_{isa}',PARENT/compiler/f'bench_eigen_{isa}',False) for isa in ['sse','avx2']]
    config[compiler]+=[(f'common_{isa}',PARENT/compiler/'bench_selected',isa=='sse') for isa in ['sse','avx2']]
cycles=2 if args.stage=='screen' else 6
results=[]
with (OUT/(args.stage+'-timing.jsonl')).open('w') as log:
 for cycle in range(cycles):
  for compiler in (['gcc','clang'] if cycle%2==0 else ['clang','gcc']):
   order=config[compiler];order=order[cycle%len(order):]+order[:cycle%len(order)]
   if cycle%2:order=order[::-1]
   for label,binary,force in order:
    env=os.environ.copy();env.pop('NATIVE_NN_FORCE_SSE',None)
    if force:env['NATIVE_NN_FORCE_SSE']='1'
    env['NATIVE_NN_REPEATS']='2' if args.stage=='screen' else '5'
    load=os.getloadavg()
    output=subprocess.check_output(['taskset','-c','16',str(binary),'time',str(INPUT),'100000','unused'],text=True,env=env)
    row=dict(compiler=compiler,cycle=cycle+1,label=label,**json.loads(output),load_start=load,load_end=os.getloadavg())
    results.append(row);log.write(json.dumps(row)+'\n');log.flush()
   print(args.stage,cycle+1,compiler,flush=True)
summary={compiler:{label:{'mean_us':statistics.mean(v:=[r['us'] for r in results if r['compiler']==compiler and r['label']==label]),'sd_us':statistics.stdev(v),'cycles':len(v)} for label,_,_ in config[compiler]} for compiler in config}
(OUT/(args.stage+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
