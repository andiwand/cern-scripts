#!/usr/bin/env python3
import json,os,statistics,subprocess
from pathlib import Path
ROOT=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
OUT=Path(os.environ.get('NATIVE_NN_RUN_ROOT',str(ROOT/'runtime-mr')))/'standalone';INPUT=ROOT.parent/'nn-inference/captured-inputs.bin'
rows=[]
with (OUT/'timing.jsonl').open('w') as log:
 for cycle in range(6):
  for compiler in (['gcc','clang'] if cycle%2==0 else ['clang','gcc']):
   order=['native_auto','native_sse','eigen_avx2','eigen_sse']
   if cycle%2:order=order[::-1]
   for label in order:
    env=os.environ.copy();env['NATIVE_NN_REPEATS']='5';env.pop('NATIVE_NN_FORCE_SSE',None)
    if label=='native_sse':env['NATIVE_NN_FORCE_SSE']='1'
    binary=OUT/f'bench_{compiler}' if label.startswith('native') else ROOT/'cxxutils'/compiler/f'bench_{label}'
    output=subprocess.check_output(['taskset','-c','16',str(binary),'time',str(INPUT),'100000','unused'],text=True,env=env)
    row=dict(compiler=compiler,cycle=cycle+1,label=label,**json.loads(output));rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
   print(cycle+1,compiler,flush=True)
summary={c:{label:{'mean_us':statistics.mean(v:=[r['us'] for r in rows if r['compiler']==c and r['label']==label]),'sd_us':statistics.stdev(v),'cycles':len(v)} for label in ['native_auto','native_sse','eigen_avx2','eigen_sse']} for c in ['gcc','clang']}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
