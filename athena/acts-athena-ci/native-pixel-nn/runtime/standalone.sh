#!/usr/bin/env bash
# Build standalone clients against the actual Athena library and a Clang copy.
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-runtime-standalone-env.log 2>&1
set -eo pipefail
runtime_root=/home/astefl/source/acts/acts-athena-ci
runtime_pkg=$runtime_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
runtime_out=${NATIVE_NN_RUN_ROOT:-$runtime_root/run/native-pixel-nn/mr-review}/standalone
runtime_build=$runtime_root/athena-build-native-pixel-nn
mkdir -p "$runtime_out/clang"
source "$runtime_build/x86_64-el9-gcc15-opt/setup.sh" >> /tmp/native-runtime-standalone-env.log 2>&1
set -u
cp /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/runtime/bench.cxx "$runtime_out/bench.cxx"
runtime_includes=(-I"$runtime_pkg" -I"$NN_STUDY_EXTERNALS/include" -I"$runtime_root/athena-native-pixel-nn/Control/CxxUtils" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -I"$NN_STUDY_LCG/Boost/1.91.0/x86_64-el9-gcc15-opt/include")
g++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 "${runtime_includes[@]}" "$runtime_out/bench.cxx" -L"$runtime_build/x86_64-el9-gcc15-opt/lib" -lSiClusterizationToolLib -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$runtime_build/x86_64-el9-gcc15-opt/lib:$NN_STUDY_EXTERNALS/lib" -o "$runtime_out/bench_gcc"
for runtime_source in NativePixelClusterNN NativePixelClusterNNBaseline NativePixelClusterNNAvx2; do
 runtime_flags=(-DSICLUSTERIZATION_NATIVE_NN_HAVE_AVX2)
 if [[ $runtime_source == *Baseline || $runtime_source == *Avx2 ]]; then runtime_flags+=(-fvisibility=hidden -fvisibility-inlines-hidden '-DEIGEN_STRONG_INLINE=inline __attribute__((always_inline))'); fi
 if [[ $runtime_source == *Avx2 ]]; then runtime_flags+=(-mavx2 -mfma -DEIGEN_MAX_ALIGN_BYTES=16); fi
 /usr/bin/clang++ -O2 -DNDEBUG -std=c++23 -fPIC -march=x86-64-v2 "${runtime_flags[@]}" "${runtime_includes[@]}" -c "$runtime_pkg/src/$runtime_source.cxx" -o "$runtime_out/clang/$runtime_source.o"
done
/usr/bin/clang++ -shared "$runtime_out/clang/"*.o -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$runtime_out/clang/libNativeRuntime.so"
/usr/bin/clang++ -O2 -DNDEBUG -std=c++23 -march=x86-64-v2 "${runtime_includes[@]}" "$runtime_out/bench.cxx" -L"$runtime_out/clang" -lNativeRuntime -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$runtime_out/clang:$NN_STUDY_EXTERNALS/lib" -o "$runtime_out/bench_clang"
for runtime_compiler in gcc clang; do
 mkdir -p "$runtime_out/$runtime_compiler/validation"
 cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$runtime_out/$runtime_compiler/validation/original.bin"
 "$runtime_out/bench_$runtime_compiler" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$runtime_out/$runtime_compiler/validation/auto.bin"
 NATIVE_NN_FORCE_SSE=1 "$runtime_out/bench_$runtime_compiler" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$runtime_out/$runtime_compiler/validation/sse.bin"
 cmp "$runtime_out/$runtime_compiler/validation/auto.bin" "$runtime_root/run/native-pixel-nn/cxxutils/tuning/$runtime_compiler/validation/tuned.bin"
 cmp "$runtime_out/$runtime_compiler/validation/sse.bin" "$runtime_root/run/native-pixel-nn/cxxutils/tuning/$runtime_compiler/validation/forced_sse.bin"
 python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$runtime_out/$runtime_compiler/validation" > "$runtime_out/$runtime_compiler/validation/report.txt"
done
