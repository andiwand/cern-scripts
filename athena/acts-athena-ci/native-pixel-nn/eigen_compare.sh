#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-eigen-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_pkg=$native_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
native_out=$native_root/run/native-pixel-nn
native_eigen=$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3
if [[ ! -d $native_eigen ]]; then native_eigen=$(find "$NN_STUDY_LCG/eigen" -type d -name eigen3 | head -1); fi
for native_impl in intrinsics eigen; do
 native_src=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/fixtures/BlockedEigenKernel.cxx
 if [[ $native_impl == intrinsics ]]; then native_src=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/fixtures/IntrinsicKernel.cxx; fi
 g++ -fPIC -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$native_pkg" -I"$native_eigen" -c "$native_src" -o "$native_out/$native_impl.o"
 objdump -Cd "$native_out/$native_impl.o" > "$native_out/$native_impl.asm"
done
native_openssl=$(sed -n 's|^OPENSSL_INCLUDE_DIR:PATH=||p' "$native_root/athena-build-native-pixel-nn/CMakeCache.txt")
native_crypto=$(sed -n 's|^OPENSSL_CRYPTO_LIBRARY:FILEPATH=||p' "$native_root/athena-build-native-pixel-nn/CMakeCache.txt")
g++ -fPIC -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$native_pkg" -I"$NN_STUDY_EXTERNALS/include" -I"$native_openssl" -c "$native_pkg/src/NativePixelClusterNNFromOnnx.cxx" -o "$native_out/loader.o"
g++ -fPIC -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 -I"$native_pkg" -I"$NN_STUDY_EXTERNALS/include" -c /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/bench.cxx -o "$native_out/bench.o"
for native_impl in intrinsics eigen; do
 g++ -shared "$native_out/loader.o" "$native_out/$native_impl.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime "$native_crypto" -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$native_out/libNative_$native_impl.so"
 g++ "$native_out/bench.o" -L"$native_out" -lNative_$native_impl -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$native_out:$NN_STUDY_EXTERNALS/lib" -o "$native_out/bench_$native_impl"
done
