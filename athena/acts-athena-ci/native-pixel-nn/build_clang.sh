#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-clang-env.log 2>&1
set -e
clang_root=/home/astefl/source/acts/acts-athena-ci
clang_pkg=$clang_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
clang_out=$clang_root/run/native-pixel-nn/clang
mkdir -p "$clang_out"
/usr/bin/clang++ -O2 -DNDEBUG -std=c++23 -fPIC -march=x86-64-v2 -I"$clang_pkg" -I"$NN_STUDY_EXTERNALS/include" -c "$clang_pkg/src/NativePixelClusterNNFromOnnx.cxx" -o "$clang_out/loader.o"
for clang_isa in sse avx2 intrinsics; do
 clang_flags='-march=x86-64-v2'
 clang_source=$clang_pkg/src/NativePixelClusterNN.cxx
 if [[ $clang_isa == avx2 ]]; then clang_flags="$clang_flags -mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16"; fi
 if [[ $clang_isa == intrinsics ]]; then clang_source=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/fixtures/IntrinsicKernel.cxx; fi
 /usr/bin/clang++ -O2 -DNDEBUG -std=c++23 -fPIC $clang_flags -I"$clang_pkg" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$clang_source" -o "$clang_out/$clang_isa.o"
 /usr/bin/clang++ -shared "$clang_out/loader.o" "$clang_out/$clang_isa.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$clang_out/libNative_$clang_isa.so"
 /usr/bin/clang++ "$clang_out/../bench.o" -L"$clang_out" -lNative_$clang_isa -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$clang_out:$NN_STUDY_EXTERNALS/lib" -o "$clang_out/bench_$clang_isa"
done
