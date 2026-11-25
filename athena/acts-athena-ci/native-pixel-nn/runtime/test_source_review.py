#!/usr/bin/env python3
"""Compare the explicit ISA wrappers with the frozen pre-review Athena library."""
import array,json,os,statistics,subprocess
from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
out=r/'test-source-review';bench=r/'generic/full/standalone/bench'
inputs=r.parent/'nn-inference/captured-inputs.bin'
checks={};rows=[]
for mode in ('auto','sse'):
 env=os.environ.copy();env.pop('LD_PRELOAD',None);env.pop('NATIVE_NN_FORCE_ONNX',None);env.pop('NATIVE_NN_FORCE_SSE',None)
 if mode=='sse':env['NATIVE_NN_FORCE_SSE']='1'
 subprocess.run([str(bench),'dump',str(inputs),'100000',str(out/(mode+'.bin'))],env=env,check=True)
 old=array.array('f');old.frombytes((r/'generic/full/standalone'/(mode+'.bin')).read_bytes())
 new=array.array('f');new.frombytes((out/(mode+'.bin')).read_bytes())
 assert len(new)==len(old)==100000*33
 checks[mode]=dict(inputs=100000,heads=4,bit_identical=new==old,max_abs=max(abs(a-b) for a,b in zip(old,new)))
 assert old==new
# Clang previously agreed exactly with the frozen aligned candidate on this capture.
for mode in ('auto','sse'):
 old=(r/'mr-review/alignment/align64/clang'/(mode+'.bin')).read_bytes()
 new=(out/'standalone/clang'/(mode+'.bin')).read_bytes()
 assert old==new
 checks['clang_'+mode]=dict(inputs=10000,heads=4,bit_identical=True)
for cycle in range(3):
 for mode in ('auto','sse'):
  for version in (('before','after') if cycle%2==0 else ('after','before')):
   env=os.environ.copy();env['NATIVE_NN_REPEATS']='3'
   env.pop('LD_PRELOAD',None);env.pop('NATIVE_NN_FORCE_ONNX',None);env.pop('NATIVE_NN_FORCE_SSE',None)
   if version=='before':env['LD_PRELOAD']=str(out/'before.so')
   if mode=='sse':env['NATIVE_NN_FORCE_SSE']='1'
   result=json.loads(subprocess.check_output(['taskset','-c','16',str(bench),'time',str(inputs),'50000','unused'],env=env,text=True))
   rows.append(dict(cycle=cycle+1,mode=mode,version=version,**result))
summary={}
for mode in ('auto','sse'):
 before=[x['us'] for x in rows if x['mode']==mode and x['version']=='before']
 after=[x['us'] for x in rows if x['mode']==mode and x['version']=='after']
 summary[mode]=dict(before_us=statistics.mean(before),after_us=statistics.mean(after),after_sd=statistics.stdev(after),change_pct=statistics.mean(100*(b/a-1) for a,b in zip(before,after)))
result=dict(numerics=checks,timing=summary,cycles=rows)
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
