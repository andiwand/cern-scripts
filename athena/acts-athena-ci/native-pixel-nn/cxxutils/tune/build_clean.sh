#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-clean-env.log 2>&1
set -euo pipefail
clean_root=/home/astefl/source/acts/acts-athena-ci
clean_parent=$clean_root/run/native-pixel-nn/cxxutils
clean_out=$clean_parent/tuning/clean
python3 /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/cxxutils/tune/clean.py
for clean_compiler in gcc clang; do
  clean_cxx=g++
  if [[ $clean_compiler == clang ]]; then clean_cxx=/usr/bin/clang++; fi
  clean_dir=$clean_out/$clean_compiler
  mkdir -p "$clean_dir"
  for clean_isa in Sse Avx2; do
    clean_extra=()
    if [[ $clean_isa == Avx2 ]]; then clean_extra=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
    "$clean_cxx" -O2 -DNDEBUG -std=c++23 -fPIC -fvisibility=hidden -fvisibility-inlines-hidden -march=x86-64-v2 "${clean_extra[@]}" -I"$clean_out" -I"$clean_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$clean_out/$clean_isa.cxx" -o "$clean_dir/$clean_isa.o"
  done
  "$clean_cxx" -shared "$clean_parent/$clean_compiler/"{Loader,Dispatch}.o "$clean_dir/"{Sse,Avx2}.o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$clean_dir/libClean.so"
  "$clean_cxx" "$clean_parent/$clean_compiler/bench.o" -L"$clean_dir" -lClean -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib:$clean_dir" -o "$clean_dir/bench"
  "$clean_dir/bench" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$clean_dir/avx2.bin"
  NATIVE_NN_FORCE_SSE=1 "$clean_dir/bench" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$clean_dir/sse.bin"
  cmp "$clean_dir/avx2.bin" "$clean_parent/tuning/$clean_compiler/validation/tuned.bin"
  cmp "$clean_dir/sse.bin" "$clean_parent/tuning/$clean_compiler/validation/forced_sse.bin"
done
