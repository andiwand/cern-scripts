#!/usr/bin/env bash
# Fresh full validation of the common-interface runtime-sized implementation.
set -euo pipefail
full_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
full_root=/home/astefl/source/acts/acts-athena-ci
full_out=$full_root/run/native-pixel-nn/generic/full
full_input=$full_root/run/edge-holes/input/RDO.39626672._000001.pool.root.1
python3 "$full_scripts/runtime/generic_prepare.py"
unset NATIVE_NN_STAGE NATIVE_NN_THRESHOLD NATIVE_NN_MODEL_DIR
bash "$full_scripts/runtime/generic_actual.sh" > "$full_out/standalone/validation.log" 2>&1
for full_backend in Native OnnxRuntime; do
 bash "$full_scripts/run.sh" "$full_out/physics/$full_backend" "$full_backend" 100 "$full_input" 4
 bash "$full_scripts/extract.sh" "$full_out/physics/$full_backend" 100 > "$full_out/physics/$full_backend/extract.log" 2>&1
done
for full_cycle in 1 2 3; do
 full_order='OnnxRuntime Native'
 if ((full_cycle%2==0)); then full_order='Native OnnxRuntime'; fi
 for full_backend in $full_order; do
  taskset -c 16 bash "$full_scripts/run.sh" "$full_out/timing/c$full_cycle/$full_backend" "$full_backend" 20 "$full_input" 0
 done
done
for full_stage in pre default-threshold; do
 for full_backend in OnnxRuntime Native; do
  if [[ $full_stage == pre ]]; then export NATIVE_NN_STAGE=pre NATIVE_NN_THRESHOLD=0; else export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=15000; fi
  full_selection=$full_backend
  if [[ $full_backend == Native ]]; then full_selection=Default; fi
  bash "$full_scripts/run.sh" "$full_out/smoke-$full_stage/$full_backend" "$full_selection" 2 "$full_input" 0
 done
done
export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=0 NATIVE_NN_MODEL_DIR=$full_out/fallback-models
bash "$full_scripts/run.sh" "$full_out/smoke-fallback/Native" Native 2 "$full_input" 0
unset NATIVE_NN_MODEL_DIR NATIVE_NN_STAGE NATIVE_NN_THRESHOLD
python3 "$full_scripts/runtime/generic_analyze.py" "$full_out" > "$full_out/analysis.log"
NATIVE_NN_RUN_ROOT=$full_out bash "$full_scripts/runtime/check_off_restore.sh" > "$full_out/off-restore.log" 2>&1
printf 'FULL VALIDATION COMPLETE\n'
