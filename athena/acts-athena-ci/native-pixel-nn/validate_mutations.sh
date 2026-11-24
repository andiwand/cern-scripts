#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-mutations-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn
mkdir -p "$native_out/validation-weights"
"$native_out/bench_eigen" dump "$NN_STUDY_ROOT/captured-inputs.bin" 1000 "$native_out/validation-weights/eigen.bin" "$native_out/mutations/weights"
export NN_STUDY_MODEL_DIR="$native_out/mutations/weights"
"$NN_STUDY_ROOT/build/bench" dump original "$NN_STUDY_ROOT/captured-inputs.bin" "$native_out/validation-weights/original.bin" 1000
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_out/validation-weights"
for native_case in nonfinite normalization activation shape missing dtype; do
 if "$native_out/bench_eigen" dump "$NN_STUDY_ROOT/captured-inputs.bin" 1 "$native_out/mutations/$native_case/output.bin" "$native_out/mutations/$native_case" > "$native_out/mutations/$native_case/test.log" 2>&1; then
  echo "Incorrectly accepted $native_case";exit 1
 fi
 echo "Rejected $native_case"
done
