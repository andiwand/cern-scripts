#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-validation-env.log 2>&1
set -e
native_root=/home/astefl/source/acts/acts-athena-ci/run
mkdir -p "$native_root/native-pixel-nn/validation"
for native_impl in intrinsics eigen; do
 "$native_root/native-pixel-nn/bench_$native_impl" dump "$native_root/nn-inference/captured-inputs.bin" 100000 "$native_root/native-pixel-nn/validation/$native_impl.bin"
done
cp "$native_root/nn-inference/validation-real-athena/original.bin" "$native_root/native-pixel-nn/validation/original.bin"
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$native_root/native-pixel-nn/validation"
cmp "$native_root/native-pixel-nn/validation/intrinsics.bin" "$native_root/native-pixel-nn/validation/eigen.bin"
