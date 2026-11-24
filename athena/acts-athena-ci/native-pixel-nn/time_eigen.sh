#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-eigen-time-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn
: > "$native_out/eigen-timing.jsonl"
for native_cycle in {1..8}; do
 native_order='intrinsics eigen'
 if ((native_cycle%2==0)); then native_order='eigen intrinsics'; fi
 for native_impl in $native_order; do
  native_result=$(taskset -c 16 "$native_out/bench_$native_impl" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused)
  printf '{"cycle":%s,"backend":"%s","result":%s}\n' "$native_cycle" "$native_impl" "$native_result" >> "$native_out/eigen-timing.jsonl"
 done
done
cat "$native_out/eigen-timing.jsonl"
