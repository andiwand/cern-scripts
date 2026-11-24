#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-check-clang-env.log 2>&1
set -e
clang_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/clang
mkdir -p "$clang_out/validation"
for clang_isa in sse avx2 intrinsics; do
 "$clang_out/bench_$clang_isa" dump "$NN_STUDY_ROOT/captured-inputs.bin" 100000 "$clang_out/validation/$clang_isa.bin"
done
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$clang_out/validation/original.bin"
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/validate.py "$clang_out/validation" > "$clang_out/validation/report.txt"
: > "$clang_out/timing.jsonl"
for clang_cycle in {1..6}; do
 clang_order='intrinsics sse avx2'
 if ((clang_cycle%2==0)); then clang_order='avx2 sse intrinsics'; fi
 for clang_isa in $clang_order; do
  clang_result=$(taskset -c 16 "$clang_out/bench_$clang_isa" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused)
  printf '{"cycle":%s,"isa":"%s","result":%s}\n' "$clang_cycle" "$clang_isa" "$clang_result" >> "$clang_out/timing.jsonl"
 done
done
