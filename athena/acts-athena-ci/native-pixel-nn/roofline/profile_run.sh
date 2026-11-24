#!/bin/bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-profile-run-env.log 2>&1
set -e
roof_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/roofline
export NATIVE_NN_REPEATS=20
for roof_variant in general_silu general_silu_avx2; do
 perf stat -x, -e cycles,instructions,cache-references,cache-misses -o "$roof_out/$roof_variant.perf-stat.csv" -- taskset -c 16 "$roof_out/bench_$roof_variant" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused > "$roof_out/$roof_variant.profile-time.json"
 perf record -F 199 -e cycles:u -o "$roof_out/$roof_variant.perf.data" -- taskset -c 16 "$roof_out/bench_$roof_variant" time "$NN_STUDY_ROOT/captured-inputs.bin" 100000 unused > "$roof_out/$roof_variant.sample-time.json" 2> "$roof_out/$roof_variant.record.log"
 perf report -i "$roof_out/$roof_variant.perf.data" --stdio --no-children --percent-limit 0.5 > "$roof_out/$roof_variant.profile.txt"
done
