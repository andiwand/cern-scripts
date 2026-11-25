#!/usr/bin/env bash
generic_out=${1:-${NATIVE_NN_RUN_ROOT:-/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/generic/final}}
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-generic-env.log 2>&1
set -euo pipefail
generic_root=/home/astefl/source/acts/acts-athena-ci
generic_pkg=$generic_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
generic_includes=(-I"$generic_pkg" -I"$NN_STUDY_EXTERNALS/include" -I"$generic_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include")
for generic_compiler in gcc clang; do
 generic_cxx=g++
 if [[ $generic_compiler == clang ]]; then generic_cxx=/usr/bin/clang++; fi
 mkdir -p "$generic_out/$generic_compiler"
 for generic_name in NativePixelClusterNN NativePixelClusterNNBaseline NativePixelClusterNNAvx2 PixelClusterNNFactory; do
  generic_extra=(-DSICLUSTERIZATION_NATIVE_NN_HAVE_AVX2)
  if [[ $generic_name == *Baseline || $generic_name == *Avx2 ]]; then generic_extra+=(-fvisibility=hidden -fvisibility-inlines-hidden '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))'); fi
  if [[ $generic_name == *Avx2 ]]; then generic_extra+=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
  "$generic_cxx" -O2 -DNDEBUG -std=c++23 -fPIC -march=x86-64-v2 "${generic_extra[@]}" "${generic_includes[@]}" -c "$generic_pkg/src/$generic_name.cxx" -o "$generic_out/$generic_compiler/$generic_name.o"
 done
 "$generic_cxx" -shared "$generic_out/$generic_compiler/"*.o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$generic_out/$generic_compiler/libNNGeneric.so"
 "$generic_cxx" -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 "${generic_includes[@]}" /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/runtime/interface_bench.cxx -L"$generic_out/$generic_compiler" -lNNGeneric -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$generic_out/$generic_compiler:$NN_STUDY_EXTERNALS/lib" -o "$generic_out/$generic_compiler/bench"
 for generic_mode in auto sse onnx; do
  unset NATIVE_NN_FORCE_SSE NATIVE_NN_FORCE_ONNX
  if [[ $generic_mode == sse ]]; then export NATIVE_NN_FORCE_SSE=1; fi
  if [[ $generic_mode == onnx ]]; then export NATIVE_NN_FORCE_ONNX=1; fi
  "$generic_out/$generic_compiler/bench" dump "$NN_STUDY_ROOT/captured-inputs.bin" 10000 "$generic_out/$generic_compiler/$generic_mode.bin"
 done
 done
