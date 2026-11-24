#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-selected-env.log 2>&1
set -euo pipefail
vec_root=/home/astefl/source/acts/acts-athena-ci
vec_out=$vec_root/run/native-pixel-nn/cxxutils
for vec_compiler in gcc clang; do
  vec_cxx=g++
  if [[ $vec_compiler == clang ]]; then vec_cxx=/usr/bin/clang++; fi
  vec_dir=$vec_out/$vec_compiler
  read -r vec_sse vec_avx2 < <(python3 - "$vec_out/selected.json" "$vec_compiler" <<'PY'
import json,sys
row=json.load(open(sys.argv[1]))[sys.argv[2]]
print(row['sse'],row['avx2'])
PY
)
  for vec_mode in selected direct_sse direct_avx2; do
    vec_dispatch=$vec_dir/Dispatch.o
    if [[ $vec_mode != selected ]]; then
      vec_define=NN_STATIC_SSE
      if [[ $vec_mode == direct_avx2 ]]; then vec_define=NN_STATIC_AVX2; fi
      vec_dispatch=$vec_dir/Dispatch_$vec_mode.o
      "$vec_cxx" -O2 -DNDEBUG -std=c++23 -fPIC -march=x86-64-v2 -I"$vec_out" -D"$vec_define" -c "$vec_out/Dispatch.cxx" -o "$vec_dispatch"
    fi
    "$vec_cxx" -shared "$vec_dir/"{Loader,Activation}.o "$vec_dispatch" "$vec_dir/Sse_b$vec_sse.o" "$vec_dir/Avx2_b$vec_avx2.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$vec_dir/libVec_$vec_mode.so"
    "$vec_cxx" "$vec_dir/bench.o" -L"$vec_dir" -lVec_"$vec_mode" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib:$vec_dir" -o "$vec_dir/bench_$vec_mode"
  done
done
