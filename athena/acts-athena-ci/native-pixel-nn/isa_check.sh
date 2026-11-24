#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-isa-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_pkg=$native_root/athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool
native_out=$native_root/run/native-pixel-nn
mkdir -p "$native_out/validation-final-isa"
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$native_out/validation-final-isa/original.bin"
for native_mode in sse2 scalar rowmajor; do
 native_flags='-march=x86-64'
 if [[ $native_mode == scalar ]]; then native_flags="$native_flags -DEIGEN_DONT_VECTORIZE -fno-tree-vectorize"; fi
 if [[ $native_mode == rowmajor ]]; then native_flags="$native_flags -DEIGEN_DEFAULT_TO_ROW_MAJOR"; fi
 g++ -O2 -DNDEBUG -std=c++23 -fPIC $native_flags -I"$native_pkg" -I"$NN_STUDY_LCG/eigen/3.4.1/x86_64-el9-gcc15-opt/include/eigen3" -c "$native_pkg/src/NativePixelClusterNN.cxx" -o "$native_out/$native_mode.o"
 native_crypto=$(sed -n 's|^OPENSSL_CRYPTO_LIBRARY:FILEPATH=||p' "$native_root/athena-build-native-pixel-nn/CMakeCache.txt")
 g++ "$native_out/bench.o" "$native_out/loader.o" "$native_out/$native_mode.o" -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime "$native_crypto" -Wl,-rpath,"$NN_STUDY_EXTERNALS/lib" -o "$native_out/bench_$native_mode"
 "$native_out/bench_$native_mode" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$native_out/validation-final-isa/$native_mode.bin"

done
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_out/validation-final-isa" > "$native_out/validation-final-isa/report.txt"
python3 - "$native_out/validation-final-isa/validation.json" <<'CHECK'
import json,sys
report=json.load(open(sys.argv[1]))
assert all(v['argmax_changes']==0 and v['elements_outside_1e-5_plus_1e-4_relative']==0 for v in report['backends'].values())
print('SSE2, scalar and row-major defaults: all comparisons passed')
CHECK
