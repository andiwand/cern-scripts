#!/usr/bin/env python3
"""Copy compact evidence into the dated note; leave raw jobs in the run directory."""
import hashlib,json,shutil,subprocess
from datetime import datetime,timezone
from pathlib import Path
A=Path('/home/astefl/source/acts/acts-athena-ci')
R=A/'run/native-pixel-nn'
N=Path('/home/astefl/notes/atlas/tsi/notebook/2026-11-24_native-pixel-nn')
N.mkdir(exist_ok=True)
files={'summary.json':'summary.json','loc.json':'loc.json',
       'default-final-ctest.log':'default-ctest.txt','avx2-ctest.log':'avx2-ctest.txt',
       'physics/record-comparison.json':'record-comparison.json',
       'physics/record-comparison-Native-avx2.json':'record-comparison-avx2.json',
       'physics/avx2-summary.json':'physics-avx2.json',
       'validation-production/validation.json':'validation-sse.json',
       'validation-production-avx2/validation.json':'validation-avx2.json',
       'validation-final-isa/validation.json':'validation-other-isa.json',
       'validation-weights/validation.json':'validation-changed-weights.json',
       'clang/summary.json':'clang.json','optimization/general-summary.json':'kernel-timing.json',
       'dispatch/symbol-audit.json':'dispatch-symbols.json',
       'roofline/summary.json':'roofline.json','roofline/bias/summary.json':'bias-trial.json',
       'eigen-timing.jsonl':'intrinsics-eigen-timing.jsonl',
       'optimization/general-timing.jsonl':'kernel-timing.jsonl',
       'roofline/sse.jsonl':'roofline-sse.jsonl','roofline/avx2.jsonl':'roofline-avx2.jsonl'}
for suffix in ['png','svg','pdf']:files['roofline/roofline.'+suffix]='roofline.'+suffix
for src,dest in files.items():
 shutil.copyfile(R/src,N/dest)
 if Path(dest).suffix in ['.txt','.svg']:
  target=N/dest
  target.write_text('\n'.join(line.rstrip() for line in target.read_text().splitlines()).rstrip()+'\n')
def git(*args):return subprocess.check_output(['git','-C',str(A/'athena-native-pixel-nn'),*args],text=True).strip()
source=A/'athena-native-pixel-nn'
paths=git('diff','--name-only','41da040949efeca5de0e5adbd84054868a5165c6').splitlines()
provenance={'date':'2026-11-24','generated_utc':datetime.now(timezone.utc).isoformat(),
 'source_branch':git('branch','--show-current'),'source_commit':git('rev-parse','HEAD'),
 'scripts_commit':subprocess.check_output(['git','-C','/home/astefl/scripts','rev-parse','HEAD'],text=True).strip(),
 'base_commit':'41da040949efeca5de0e5adbd84054868a5165c6',
 'source_sha256':{p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in paths},
 'nightly':'2026-11-23T2100','platform':'x86_64-el9-gcc15-opt','compiler':'GCC 15.2','acts':'48.5.0',
 'onnxruntime':'1.26','eigen':'3.4.1','host':'AMD Threadripper 3970X','timed_cpu':16,
 'input':str(A/'run/edge-holes/input/RDO.39626672._000001.pool.root.1'),
 'scripts':'athena/acts-athena-ci/native-pixel-nn in https://github.com/andiwand/cern-scripts',
 'result_directory':str(R),'job_library_hashes':{},'models':{},
 'validation_limits':['100 ttbar events, no claim of bitwise fitted parameters or universal branching equivalence.',
 'Full Athena CPU comparison uses GCC/SSE; AVX2 physics and standalone GCC/Clang timing are separate.',
 'Final explicit column-major map preserves the measured SSE library text section exactly.',
 'Bias-initialized GEMV is a standalone follow-up trial, excluded from the MR candidate.']}
for p in sorted(R.glob('physics/*/libraries.txt')):
 if p.parent.name in ['OnnxRuntime','Native','Native-avx2']:provenance['job_library_hashes'][str(p.relative_to(R))]=p.read_text().splitlines()
modeldir=Path('/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01')
for p in sorted(modeldir.glob('*.onnx')):provenance['models'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
provenance['harness_incidents']={
 'ORT_physics_wrapper':json.loads((R/'physics/OnnxRuntime/wrapper-recovery.json').read_text()),
 'default_threshold_smoke':(R/'smoke-default-threshold/OnnxRuntime-inspection-failure/cause.txt').read_text()}
(N/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(N)
