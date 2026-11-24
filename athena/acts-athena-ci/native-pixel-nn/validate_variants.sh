#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-opt-validation-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/optimization
mkdir -p "$native_out/validation"
for native_variant in eigen vector_silu avx2 avx2_vector_silu gemv gemv_vector_silu; do
 "$native_out/bench_$native_variant" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$native_out/validation/$native_variant.bin"
done
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$native_out/validation/original.bin"
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_out/validation" > "$native_out/validation/report.txt"
