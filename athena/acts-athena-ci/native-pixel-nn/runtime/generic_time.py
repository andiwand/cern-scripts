#!/usr/bin/env python3
import array,json,os,statistics,subprocess
from pathlib import Path
base=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
r=Path(os.environ.get('NATIVE_NN_RUN_ROOT',base/'generic/final'))
inputs=base.parent/'nn-inference/captured-inputs.bin'
rows=[];checks={}
for compiler in ('gcc','clang'):
 checks[compiler]={}
 for mode in ('auto','sse'):
  before=array.array('f');after=array.array('f')
  with (base/'mr-review/alignment/align64'/compiler/(mode+'.bin')).open('rb') as f: before.frombytes(f.read())
  with (r/compiler/(mode+'.bin')).open('rb') as f: after.frombytes(f.read())
  assert len(before)==len(after)
  violations=sum(abs(a-b)>1e-5+1e-4*abs(a) for a,b in zip(before,after))
  argmax=sum(max(range(3),key=lambda j:before[i+j])!=max(range(3),key=lambda j:after[i+j]) for i in range(0,len(before),33))
  checks[compiler][mode]=dict(bit_identical=before==after,max_abs=max(abs(a-b) for a,b in zip(before,after)),outside_tolerance=violations,argmax_changes=argmax)
  assert violations==argmax==0
for compiler in ('gcc','clang'):
 reference=array.array('f');reference.frombytes((r/compiler/'onnx.bin').read_bytes())
 for mode in ('auto','sse'):
  actual=array.array('f');actual.frombytes((r/compiler/(mode+'.bin')).read_bytes())
  assert len(actual)==len(reference)
  violations=sum(abs(a-b)>1e-5+1e-4*abs(b) for a,b in zip(actual,reference))
  argmax=sum(max(range(3),key=lambda j:actual[i+j])!=max(range(3),key=lambda j:reference[i+j]) for i in range(0,len(actual),33))
  checks[compiler][mode]['vs_onnx']=dict(max_abs=max(abs(a-b) for a,b in zip(actual,reference)),outside_tolerance=violations,argmax_changes=argmax)
  assert violations==argmax==0
with (r/'timing.jsonl').open('w') as log:
 for cycle in range(3):
  for compiler in ('gcc','clang'):
   for mode in ('auto','sse'):
    for version in (('before','after') if cycle%2==0 else ('after','before')):
     env=os.environ.copy();env['NATIVE_NN_REPEATS']='3';env.pop('NATIVE_NN_FORCE_SSE',None);env.pop('NATIVE_NN_FORCE_ONNX',None);env.pop('LD_PRELOAD',None)
     if mode=='sse':env['NATIVE_NN_FORCE_SSE']='1'
     binary=r/compiler/'bench'
     if version=='before':
      binary=base/'generic/baseline/bench_gcc' if compiler=='gcc' else base/'generic/baseline/clang/bench'
      library=base/'generic/baseline/libSiClusterizationToolLib.so' if compiler=='gcc' else base/'generic/baseline/clang/libAlignment.so'
      env['LD_PRELOAD']=str(library)
     output=subprocess.check_output(['taskset','-c','16',str(binary),'time',str(inputs),'50000','unused'],text=True,env=env)
     row=dict(compiler=compiler,mode=mode,version=version,cycle=cycle+1,**json.loads(output))
     rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
  print('cycle',cycle+1,flush=True)
summary={}
for c in ('gcc','clang'):
 summary[c]={}
 for mode in ('auto','sse'):
  a=[r['us'] for r in rows if (r['compiler'],r['mode'],r['version'])==(c,mode,'before')]
  b=[r['us'] for r in rows if (r['compiler'],r['mode'],r['version'])==(c,mode,'after')]
  summary[c][mode]=dict(before_us=statistics.mean(a),after_us=statistics.mean(b),after_sd=statistics.stdev(b),change_percent=statistics.mean(100*(v/u-1) for u,v in zip(a,b)))
(r/'summary.json').write_text(json.dumps(dict(numerics=checks,timing=summary),indent=2)+'\n')
print(json.dumps(dict(numerics=checks,timing=summary),indent=2))

# Cached ONNX adapter through the same interface; measured after native A/B cycles.
env=os.environ.copy();env['NATIVE_NN_FORCE_ONNX']='1';env['NATIVE_NN_REPEATS']='3'
env.pop('NATIVE_NN_FORCE_SSE',None);env.pop('LD_PRELOAD',None)
values=[json.loads(subprocess.check_output(['taskset','-c','16',str(r/'gcc/bench'),'time',str(inputs),'50000','unused'],env=env,text=True)) for _ in range(3)]
onnx=dict(description='Common-interface ONNX adapter, GCC, number + selected position, 50k captured inputs x3 repeats, three sequential runs',samples=values,mean_us=statistics.mean(v['us'] for v in values),sd_us=statistics.stdev(v['us'] for v in values))
(r/'onnx-interface.json').write_text(json.dumps(onnx,indent=2)+'\n')
