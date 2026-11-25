#!/usr/bin/env python3
"""Time the actual restored Athena library only after all reconstruction/build jobs."""
import json,os,statistics,subprocess
from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/generic/full/standalone')
inputs=r.parents[3]/'nn-inference/captured-inputs.bin'
rows=[]
for cycle in range(3):
 modes=('onnx','auto','sse') if cycle%2==0 else ('sse','auto','onnx')
 for mode in modes:
  env=os.environ.copy();env['NATIVE_NN_REPEATS']='3'
  env.pop('NATIVE_NN_FORCE_SSE',None);env.pop('NATIVE_NN_FORCE_ONNX',None);env.pop('LD_PRELOAD',None)
  if mode=='sse':env['NATIVE_NN_FORCE_SSE']='1'
  if mode=='onnx':env['NATIVE_NN_FORCE_ONNX']='1'
  result=json.loads(subprocess.check_output(['taskset','-c','16',str(r/'bench'),'time',str(inputs),'50000','unused'],env=env,text=True))
  rows.append(dict(cycle=cycle+1,mode=mode,**result))
summary={m:dict(mean_us=statistics.mean(v:=[x['us'] for x in rows if x['mode']==m]),sd_us=statistics.stdev(v)) for m in ('onnx','auto','sse')}
result=dict(method='Actual Athena GCC library; number + selected position; 3 alternating cycles x 50k inputs x3; core16; no concurrent reconstruction/build',summary=summary,cycles=rows)
(r/'timing.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
