#!/usr/bin/env bash
# Re-run isolated timing, integration and physics sequentially on the final build.
set -euo pipefail
runtime_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
runtime_out=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/runtime-mr
runtime_input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
unset NATIVE_NN_STAGE NATIVE_NN_THRESHOLD
bash "$runtime_scripts/runtime/time.sh" > "$runtime_out/standalone/timing.log" 2>&1
for runtime_backend in Native OnnxRuntime; do
 bash "$runtime_scripts/run.sh" "$runtime_out/physics/$runtime_backend" "$runtime_backend" 100 "$runtime_input" 4
 bash "$runtime_scripts/extract.sh" "$runtime_out/physics/$runtime_backend" 100 > "$runtime_out/physics/$runtime_backend/extract.log" 2>&1
done
for runtime_cycle in 1 2 3; do
 runtime_order='OnnxRuntime Native'
 if ((runtime_cycle%2==0)); then runtime_order='Native OnnxRuntime'; fi
 for runtime_backend in $runtime_order; do
  taskset -c 16 bash "$runtime_scripts/run.sh" "$runtime_out/timing/c$runtime_cycle/$runtime_backend" "$runtime_backend" 20 "$runtime_input" 0
 done
done
for runtime_stage in pre default-threshold; do
 for runtime_backend in OnnxRuntime Native; do
  if [[ $runtime_stage == pre ]]; then export NATIVE_NN_STAGE=pre NATIVE_NN_THRESHOLD=0; else export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=15000; fi
  bash "$runtime_scripts/run.sh" "$runtime_out/smoke-$runtime_stage/$runtime_backend" "$runtime_backend" 2 "$runtime_input" 0
 done
done
