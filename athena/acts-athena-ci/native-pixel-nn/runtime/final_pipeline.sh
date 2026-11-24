#!/usr/bin/env bash
# Final measurements after the scalar debug-wrapper fix.
set -euo pipefail
final_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
final_results=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/runtime-final
final_input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
export NATIVE_NN_RUN_ROOT=$final_results
unset NATIVE_NN_STAGE NATIVE_NN_THRESHOLD
bash "$final_scripts/runtime/time.sh" > "$final_results/standalone/timing.log" 2>&1
bash "$final_scripts/run.sh" "$final_results/physics/Native" Native 100 "$final_input" 4
bash "$final_scripts/extract.sh" "$final_results/physics/Native" 100 > "$final_results/physics/Native/extract.log" 2>&1
for final_cycle in 1 2 3; do
 final_order='OnnxRuntime Native'
 if ((final_cycle%2==0)); then final_order='Native OnnxRuntime'; fi
 for final_backend in $final_order; do
  taskset -c 16 bash "$final_scripts/run.sh" "$final_results/timing/c$final_cycle/$final_backend" "$final_backend" 20 "$final_input" 0
 done
done
for final_stage in pre default-threshold; do
 if [[ $final_stage == pre ]]; then export NATIVE_NN_STAGE=pre NATIVE_NN_THRESHOLD=0; else export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=15000; fi
 bash "$final_scripts/run.sh" "$final_results/smoke-$final_stage/Native" Native 2 "$final_input" 0
done
bash "$final_scripts/runtime/ort_baseline.sh" > "$final_results/ort-baseline.log" 2>&1
python3 "$final_scripts/runtime/analyze.py" "$final_results" > "$final_results/analysis.log"
