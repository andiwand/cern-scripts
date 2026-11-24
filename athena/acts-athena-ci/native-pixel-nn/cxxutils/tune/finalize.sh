#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-tune-finalize-env.log 2>&1
set -euo pipefail
tune_parent=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils
tune_out=$tune_parent/tuning
for tune_compiler in gcc clang; do
  tune_cxx=g++
  if [[ $tune_compiler == clang ]]; then tune_cxx=/usr/bin/clang++; fi
  tune_dir=$tune_out/$tune_compiler
  for tune_mode in tuned reversed direct_sse direct_avx2; do
    tune_objects=("$tune_dir/Sse_vector_loop.o" "$tune_dir/Avx2_vector.o")
    tune_dispatch=$tune_parent/$tune_compiler/Dispatch.o
    if [[ $tune_mode == reversed ]]; then tune_objects=("$tune_dir/Avx2_vector.o" "$tune_dir/Sse_vector_loop.o"); fi
    if [[ $tune_mode == direct* ]]; then tune_dispatch=$tune_parent/$tune_compiler/Dispatch_$tune_mode.o; fi
    "$tune_cxx" -shared "$tune_parent/$tune_compiler/Loader.o" "$tune_dispatch" "${tune_objects[@]}" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$tune_dir/libTune_$tune_mode.so"
    "$tune_cxx" "$tune_parent/$tune_compiler/bench.o" -L"$tune_dir" -lTune_"$tune_mode" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib:$tune_dir" -o "$tune_dir/bench_$tune_mode"
  done
  mkdir -p "$tune_dir/validation"
  cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$tune_dir/validation/original.bin"
  for tune_case in tuned forced_sse reversed reversed_sse direct_sse direct_avx2; do
    tune_binary=$tune_case
    tune_env=()
    if [[ $tune_case == forced_sse ]]; then tune_binary=tuned; tune_env=(NATIVE_NN_FORCE_SSE=1); fi
    if [[ $tune_case == reversed_sse ]]; then tune_binary=reversed; tune_env=(NATIVE_NN_FORCE_SSE=1); fi
    env "${tune_env[@]}" "$tune_dir/bench_$tune_binary" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$tune_dir/validation/$tune_case.bin"
  done
  cmp "$tune_dir/validation/tuned.bin" "$tune_dir/validation/reversed.bin"
  cmp "$tune_dir/validation/tuned.bin" "$tune_dir/validation/direct_avx2.bin"
  cmp "$tune_dir/validation/forced_sse.bin" "$tune_dir/validation/reversed_sse.bin"
  cmp "$tune_dir/validation/forced_sse.bin" "$tune_dir/validation/direct_sse.bin"
  python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$tune_dir/validation" > "$tune_dir/validation/report.txt"
  python3 - "$tune_dir/validation/validation.json" <<'PY'
import json,sys
report=json.load(open(sys.argv[1]))
assert all(v['finite'] and v['argmax_changes']==0 and v['elements_outside_1e-5_plus_1e-4_relative']==0 for v in report['backends'].values())
print(sys.argv[1],': all numerical and link-order comparisons pass')
PY
done
python3 - "$tune_out" <<'PY'
import json,sys,subprocess
from pathlib import Path
p=Path(sys.argv[1]);r={}
for compiler in ['gcc','clang']:
 def symbols(file):return {line.split()[-1] for line in subprocess.check_output(['nm','-g','--defined-only',str(p/compiler/file)],text=True).splitlines() if 'Eigen' in line}
 assert not (symbols('Sse_vector_loop.o') & symbols('Avx2_vector.o'))
 for mode in ['tuned','reversed']:
  assert 'Eigen::' not in subprocess.check_output(['nm','-DC','--defined-only',str(p/compiler/f'libTune_{mode}.so')],text=True)
 r[compiler]={'sse':'vector_loop','avx2':'vector','overlapping_eigen_symbols':0,'exported_eigen_symbols':0}
(p/'selected.json').write_text(json.dumps(r,indent=2)+'\n')
PY
