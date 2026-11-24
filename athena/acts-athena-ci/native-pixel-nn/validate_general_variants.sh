#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-general-validation-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/optimization
for native_variant in general_silu general_silu_avx2 dynamic_gemv dynamic_gemv_avx2; do
 "$native_out/bench_$native_variant" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$native_out/validation/$native_variant.bin"
done
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_out/validation" > "$native_out/validation/report.txt"
