#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-dispatch-env.log 2>&1
set -e
dispatch_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/dispatch
dispatch_build=/home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn
dispatch_ssl=$(sed -n 's|^OPENSSL_INCLUDE_DIR:PATH=||p' "$dispatch_build/CMakeCache.txt")
dispatch_crypto=$(sed -n 's|^OPENSSL_CRYPTO_LIBRARY:FILEPATH=||p' "$dispatch_build/CMakeCache.txt")
for dispatch_compiler in gcc clang; do
 dispatch_cxx=g++
 if [[ $dispatch_compiler == clang ]]; then dispatch_cxx=/usr/bin/clang++; fi
 mkdir -p "$dispatch_out/$dispatch_compiler"
 for dispatch_file in Sse Avx2 Dispatch Loader bench; do
  dispatch_flags='-march=x86-64-v2'
  if [[ $dispatch_file == Avx2 ]]; then dispatch_flags="$dispatch_flags -mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16"; fi
  "$dispatch_cxx" -O2 -DNDEBUG -std=c++23 -fPIC $dispatch_flags -I"$dispatch_out" -I"$NN_STUDY_EXTERNALS/include" -I"$dispatch_ssl" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$dispatch_out/$dispatch_file.cxx" -o "$dispatch_out/$dispatch_compiler/$dispatch_file.o"
 done
 "$dispatch_cxx" -shared "$dispatch_out/$dispatch_compiler/"{Sse,Avx2,Dispatch,Loader}.o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime "$dispatch_crypto" -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$dispatch_out/$dispatch_compiler/libNativeDispatch.so"
 "$dispatch_cxx" "$dispatch_out/$dispatch_compiler/bench.o" -L"$dispatch_out/$dispatch_compiler" -lNativeDispatch -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$dispatch_out/$dispatch_compiler:$NN_STUDY_EXTERNALS/lib" -o "$dispatch_out/$dispatch_compiler/bench"
done
