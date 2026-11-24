#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-tune-env.log 2>&1
set -euo pipefail
tune_root=/home/astefl/source/acts/acts-athena-ci
tune_parent=$tune_root/run/native-pixel-nn/cxxutils
tune_out=$tune_parent/tuning
tune_here=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/cxxutils/tune
python3 "$tune_here/generate.py"
for tune_compiler in gcc clang; do
  tune_cxx=g++
  if [[ $tune_compiler == clang ]]; then tune_cxx=/usr/bin/clang++; fi
  tune_dir=$tune_out/$tune_compiler
  mkdir -p "$tune_dir"
  for tune_case in ${NATIVE_VEC_CASES:-packet unroll flat heads bias vector vector_bias vector_loop}; do
    tune_defines=()
    if [[ $tune_case != packet && $tune_case != vector_loop ]]; then tune_defines+=(-DNN_UNROLL_ACTIVATION); fi
    if [[ $tune_case == flat || $tune_case == heads || $tune_case == bias ]]; then tune_defines+=(-DNN_FLATTEN_PACKET); fi
    if [[ $tune_case == heads || $tune_case == bias || $tune_case == vector* ]]; then tune_defines+=(-DNN_LOCAL_HEADS); fi
    if [[ $tune_case == bias || $tune_case == vector_bias ]]; then tune_defines+=(-DNN_BIAS_FIRST); fi
    if [[ $tune_case == vector* ]]; then tune_defines+=(-DNN_CXX_ACTIVATION); fi
    for tune_isa in Sse Avx2; do
      tune_extra=()
      if [[ $tune_isa == Avx2 ]]; then tune_extra=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
      "$tune_cxx" -O2 -DNDEBUG -std=c++23 -fPIC -fvisibility=hidden -fvisibility-inlines-hidden -march=x86-64-v2 "${tune_extra[@]}" "${tune_defines[@]}" -DNN_BLOCKS=8 -I"$tune_out" -I"$tune_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$tune_out/$tune_isa.cxx" -o "$tune_dir/${tune_isa}_${tune_case}.o"
    done
    "$tune_cxx" -shared "$tune_parent/$tune_compiler/"{Loader,Dispatch}.o "$tune_dir/"{Sse,Avx2}_"$tune_case".o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$tune_dir/libTune_$tune_case.so"
    "$tune_cxx" "$tune_parent/$tune_compiler/bench.o" -L"$tune_dir" -lTune_"$tune_case" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib:$tune_dir" -o "$tune_dir/bench_$tune_case"
  done
done
