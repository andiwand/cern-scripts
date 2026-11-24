#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-opt-time-env.log 2>&1
set -e
native_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/optimization
: > "$native_out/general-timing.jsonl"
for native_cycle in {1..6}; do
 native_order='gemv_vector_silu general_silu dynamic_gemv gemv_avx2_vector_silu general_silu_avx2 dynamic_gemv_avx2'
 if ((native_cycle%2==0)); then native_order='dynamic_gemv_avx2 general_silu_avx2 gemv_avx2_vector_silu dynamic_gemv general_silu gemv_vector_silu'; fi
 for native_variant in $native_order; do
  native_result=$(taskset -c 16 "$native_out/bench_$native_variant" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused)
  printf '{"cycle":%s,"backend":"%s","result":%s}\n' "$native_cycle" "$native_variant" "$native_result" >> "$native_out/general-timing.jsonl"
 done
done
cat "$native_out/general-timing.jsonl"
