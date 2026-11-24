#!/bin/bash
set -eo pipefail
native_scripts=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn
native_results=/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn
native_input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
while [[ ! -f "$native_results/smoke/OnnxRuntime/exit-code.txt" ]]; do sleep 5; done
for native_backend in Native OnnxRuntime; do
 test "$(cat "$native_results/smoke/$native_backend/exit-code.txt")" = 0
 if [[ ! -f "$native_results/physics/$native_backend/exit-code.txt" ]]; then
  bash "$native_scripts/run.sh" "$native_results/physics/$native_backend" "$native_backend" 100 "$native_input" 4
 fi
 test "$(cat "$native_results/physics/$native_backend/exit-code.txt")" = 0
 if [[ ! -f "$native_results/physics/$native_backend/outcomes.txt.gz" ]]; then
  bash "$native_scripts/extract.sh" "$native_results/physics/$native_backend" 100 > "$native_results/physics/$native_backend/extract.log" 2>&1
 fi
done
for native_cycle in 1 2 3; do
 native_order='OnnxRuntime Native'
 if ((native_cycle%2==0)); then native_order='Native OnnxRuntime'; fi
 for native_backend in $native_order; do
  taskset -c 16 bash "$native_scripts/run.sh" "$native_results/timing/c$native_cycle/$native_backend" "$native_backend" 20 "$native_input" 0
 done
done
for native_stage in pre default-threshold; do
 for native_backend in OnnxRuntime Native; do
  if [[ $native_stage == pre ]]; then export NATIVE_NN_STAGE=pre NATIVE_NN_THRESHOLD=0; else export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=15000; fi
  bash "$native_scripts/run.sh" "$native_results/smoke-$native_stage/$native_backend" "$native_backend" 2 "$native_input" 0
 done
done
