#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-opt-time-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/optimization
: > "$native_out/timing.jsonl"
for native_cycle in {1..6}; do
 native_order='eigen vector_silu avx2 avx2_vector_silu gemv gemv_vector_silu avx2_four avx2_four_vector_silu gemv_avx2 gemv_avx2_vector_silu'
 if ((native_cycle%2==0)); then native_order='gemv_avx2_vector_silu gemv_avx2 avx2_four_vector_silu avx2_four gemv_vector_silu gemv avx2_vector_silu avx2 vector_silu eigen'; fi
 for native_variant in $native_order; do
  native_result=$(taskset -c 16 "$native_out/bench_$native_variant" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused)
  printf '{"cycle":%s,"backend":"%s","result":%s}\n' "$native_cycle" "$native_variant" "$native_result" >> "$native_out/timing.jsonl"
 done
done
cat "$native_out/timing.jsonl"
