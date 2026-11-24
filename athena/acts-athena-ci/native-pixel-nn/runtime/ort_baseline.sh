#!/usr/bin/env bash
# Run after reconstruction: refresh the original ONNX call-path comparison.
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-runtime-ort-env.log 2>&1
set -eo pipefail
source /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh >> /tmp/native-runtime-ort-env.log 2>&1
set -u
python3 - <<'PY'
import json,os,statistics,subprocess
from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci/run')
out=Path(os.environ.get('NATIVE_NN_RUN_ROOT',str(r/'native-pixel-nn/runtime-mr')))/'standalone'
inputs=r/'nn-inference/captured-inputs.bin'
env=os.environ.copy();env.pop('NATIVE_NN_FORCE_SSE',None);env['NATIVE_NN_REPEATS']='5'
rows=[]
for cycle in range(3):
 for backend in (['OnnxRuntime','Native'] if cycle%2==0 else ['Native','OnnxRuntime']):
  args=([str(r/'nn-inference/build/bench'),'time','original',str(inputs),'100000','1'] if backend=='OnnxRuntime'
        else [str(out/'bench_gcc'),'time',str(inputs),'100000','unused'])
  result=json.loads(subprocess.check_output(['taskset','-c','16',*args],env=env,text=True))
  rows.append({'cycle':cycle+1,'backend':backend,'us':result['cycle_us'][0] if backend=='OnnxRuntime' else result['us']})
summary={b:{'mean_us':statistics.mean(v:=[x['us'] for x in rows if x['backend']==b]),'sd_us':statistics.stdev(v)} for b in ['OnnxRuntime','Native']}
report={'method':'Three alternating pairs, 100k captured inputs; original ONNX call-path harness and actual native GCC library. Native repeats five times per observation; ONNX once. No model loading or cluster preparation. CPU 16; default harness math libraries, no extra preload.',
        'summary':summary,'cycles':rows}
(out/'ort-baseline.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
PY
