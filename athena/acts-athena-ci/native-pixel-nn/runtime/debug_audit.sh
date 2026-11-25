#!/usr/bin/env bash
# Compile only after timing/reconstruction has finished.
debug_out=${1:-${NATIVE_NN_RUN_ROOT:-/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/mr-review}}/debug-audit
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-runtime-debug-env.log 2>&1
set -euo pipefail
debug_root=/home/astefl/source/acts/acts-athena-ci
debug_pkg=$debug_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
debug_includes=(-I"$debug_pkg" -I"$debug_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include")
for debug_compiler in gcc clang; do
 debug_cxx=g++
 if [[ $debug_compiler == clang ]]; then debug_cxx=/usr/bin/clang++; fi
 for debug_mode in debug sanitize; do
  debug_flags=(-O0)
  if [[ $debug_mode == sanitize ]]; then debug_flags=(-O1 -fsanitize=address,undefined); fi
  mkdir -p "$debug_out/$debug_compiler/$debug_mode"
  for debug_isa in Baseline Avx2; do
   debug_extra=()
   if [[ $debug_isa == Avx2 ]]; then debug_extra=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
   "$debug_cxx" "${debug_flags[@]}" -std=c++23 -fPIC -march=x86-64-v2 -fvisibility=hidden -fvisibility-inlines-hidden '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))' "${debug_extra[@]}" "${debug_includes[@]}" -c "$debug_pkg/src/NativePixelClusterNN$debug_isa.cxx" -o "$debug_out/$debug_compiler/$debug_mode/$debug_isa.o"
  done
 done
done
python3 - "$debug_out" <<'PY'
import json,re,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);report={}
for compiler in ['gcc','clang']:
 report[compiler]={}
 for mode in ['debug','sanitize']:
  details={}
  for isa in ['Baseline','Avx2']:
   path=out/compiler/mode/(isa+'.o')
   assembly=subprocess.check_output(['objdump','-d','--no-show-raw-insn',str(path)],text=True)
   symbols={line.split()[-1] for line in subprocess.check_output(['nm','-g','--defined-only',str(path)],text=True).splitlines()}
   name='';avx=set()
   for line in assembly.splitlines():
    header=re.match(r'^[0-9a-f]+ <(.*)>:',line)
    if header:name=header.group(1)
    if re.match(r'^\s*[0-9a-f]+:\s+v\w+',line):avx.add(name)
   if isa=='Baseline':assert not avx,(path,avx)
   global_avx=avx&symbols
   # Helpers with an explicit eight-float vector type cannot collide with baseline helpers.
   assert all('inferAvx2' in s or 'Dv8_f' in s for s in global_avx),(path,global_avx)
   details[isa]={'avx_bearing_functions':len(avx),'avx_bearing_global_symbols':sorted(global_avx)}
  report[compiler][mode]=details
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
PY
