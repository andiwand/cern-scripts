#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-generic-actual-env.log 2>&1
source /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh >> /tmp/native-generic-actual-env.log 2>&1
set -euo pipefail
actual_root=/home/astefl/source/acts/acts-athena-ci
actual_pkg=$actual_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
actual_lib=$actual_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib
actual_out=$actual_root/run/native-pixel-nn/generic/full/standalone
actual_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/runtime
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$actual_pkg" -I"$NN_STUDY_EXTERNALS/include" -I"$actual_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include" "$actual_scripts/interface_bench.cxx" -L"$actual_lib" -lSiClusterizationToolLib -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$actual_lib:$NN_STUDY_EXTERNALS/lib" -o "$actual_out/bench"
for actual_mode in auto sse onnx; do
 unset NATIVE_NN_FORCE_SSE NATIVE_NN_FORCE_ONNX
 if [[ $actual_mode == sse ]]; then export NATIVE_NN_FORCE_SSE=1; fi
 if [[ $actual_mode == onnx ]]; then export NATIVE_NN_FORCE_ONNX=1; fi
 "$actual_out/bench" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$actual_out/$actual_mode.bin"
done
python3 - "$actual_out" <<'PY_CHECK'
import array,json,sys
from pathlib import Path
p=Path(sys.argv[1]);reference=array.array('f');reference.frombytes((p/'onnx.bin').read_bytes())
assert len(reference)==100000*33
report={}
for mode in ('auto','sse'):
 actual=array.array('f');actual.frombytes((p/(mode+'.bin')).read_bytes());assert len(actual)==len(reference)
 violations=sum(abs(a-b)>1e-5+1e-4*abs(b) for a,b in zip(actual,reference))
 choices=sum(max(range(3),key=lambda j:actual[i+j])!=max(range(3),key=lambda j:reference[i+j]) for i in range(0,len(actual),33))
 assert violations==choices==0
 report[mode]=dict(inputs=100000,heads=4,outside_tolerance=violations,argmax_changes=choices,max_abs=max(abs(a-b) for a,b in zip(actual,reference)))
(p/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
PY_CHECK
