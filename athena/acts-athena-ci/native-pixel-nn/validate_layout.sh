#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-layout-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci
native_out=$native_root/run/native-pixel-nn
source "$native_root/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh" >> /tmp/native-layout-env.log 2>&1
for native_case in weights metadata extra; do
 native_dir="$native_out/final-review/$native_case"
 mkdir -p "$native_dir"
 "$native_out/bench_production" dump "$NN_STUDY_ROOT/captured-inputs.bin" 1000 "$native_dir/native.bin" "$native_out/mutations/$native_case" > "$native_dir/load.log" 2>&1
 NN_STUDY_MODEL_DIR="$native_out/mutations/$native_case" "$NN_STUDY_ROOT/build/bench" dump original "$NN_STUDY_ROOT/captured-inputs.bin" "$native_dir/original.bin" 1000 > "$native_dir/reference.log" 2>&1
 python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_dir" > "$native_dir/report.txt"
 echo "Accepted and checked $native_case"
done
for native_case in nonfinite normalization activation shape missing dtype precision output_order; do
 if "$native_out/bench_production" dump "$NN_STUDY_ROOT/captured-inputs.bin" 1 "$native_out/final-review/unused.bin" "$native_out/mutations/$native_case" > "$native_out/final-review/reject-$native_case.log" 2>&1; then
  echo "Incorrectly accepted $native_case";exit 1
 fi
 if [[ $native_case =~ ^(normalization|activation|precision|output_order)$ ]]; then
  rg -q 'Native pixel NN disagrees with ONNX' "$native_out/final-review/reject-$native_case.log"
 fi
 echo "Rejected $native_case"
done
