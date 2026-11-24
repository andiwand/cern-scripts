#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-opt-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_pkg=$native_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
native_out=$native_root/run/native-pixel-nn/optimization
for native_variant in avx2_four avx2_four_vector_silu gemv_avx2 gemv_avx2_vector_silu; do
 native_flags='-march=x86-64-v2'
 if [[ $native_variant == *avx2* ]]; then native_flags='-march=x86-64-v2 -mavx2 -mfma'; fi
 g++ -O2 -DNDEBUG -std=c++23 -fPIC $native_flags -I"$native_pkg" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$native_out/$native_variant.cxx" -o "$native_out/$native_variant.o"
 g++ -shared "$native_out/../loader.o" "$native_out/$native_variant.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$native_out/libNative_$native_variant.so"
 g++ "$native_out/../bench.o" -L"$native_out" -lNative_$native_variant -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$native_out:$NN_STUDY_EXTERNALS/lib" -o "$native_out/bench_$native_variant"
done
