#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-production-bench-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_out=$native_root/run/native-pixel-nn
source "$native_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh" >> /tmp/native-production-bench-env.log 2>&1
g++ "$native_out/bench.o" -L"$native_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib" -lSiClusterizationToolLib -L"$NN_STUDY_EXTERNALS/lib" -lonnxruntime -Wl,-rpath,"$native_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/lib:$NN_STUDY_EXTERNALS/lib" -o "$native_out/bench_production"
native_validation="$native_out/${1:-validation-production}"
mkdir -p "$native_validation"
"$native_out/bench_production" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$native_validation/native.bin"
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$native_validation/original.bin"
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_validation" > "$native_validation/report.txt"
