#!/usr/bin/env bash
# Full sequential validation of the current build (after build.sh and tests.sh).
#   campaign.sh OUT [--input RDO] [--events 100] [--threads 4] [--timing-events 20]
#                   [--cycles 3] [--cpu 16] [--no-standalone] [--no-fallback] [--no-off-restore]
# prepare.py; standalone bench against the Athena library (100k-input auto/SSE vs ONNX,
# alternating auto/SSE/ONNX timing); Native and ONNX physics + extraction; alternating
# serial timing pairs pinned to CPU; pre/default-threshold smoke runs (native via the
# Default backend selection); incompatible-model fallback smoke; analyze.py;
# check_off_restore.sh. Do not build, edit this script or run other jobs meanwhile.
set -euo pipefail
here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
usage() { sed -n '2,9p' "$0" >&2; exit 2; }
(($#)) || usage
out=$(realpath -m "$1"); shift
input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
events=100 threads=4 timing_events=20 cycles=3 cpu=16 standalone=1 fallback=1 off_restore=1
while (($#)); do
 case $1 in
  --input) input=$(realpath "$2"); shift 2;;
  --events) events=$2; shift 2;;
  --threads) threads=$2; shift 2;;
  --timing-events) timing_events=$2; shift 2;;
  --cycles) cycles=$2; shift 2;;
  --cpu) cpu=$2; shift 2;;
  --no-standalone) standalone=0; shift;;
  --no-fallback) fallback=0; shift;;
  --no-off-restore) off_restore=0; shift;;
  *) usage;;
 esac
done
python3 "$here/prepare.py" "$out"
unset NATIVE_NN_STAGE NATIVE_NN_THRESHOLD NATIVE_NN_MODEL_DIR
if ((standalone)); then
 bash "$here/bench_build.sh" "$out/standalone" athena > "$out/standalone/build.log" 2>&1
 bench=$out/standalone/athena/bench
 modes=(auto="$bench" sse="$bench:NATIVE_NN_FORCE_SSE=1" onnx="$bench:NATIVE_NN_FORCE_ONNX=1")
 bash "$here/validate_outputs.sh" "$out/standalone" "${modes[@]}" > "$out/standalone/validation.log" 2>&1
 cases=()
 for mode in "${modes[@]}"; do cases+=(--case "$mode"); done
 bash "$here/bench_env.sh" python3 "$here/bench_time.py" --out "$out/standalone" --cpu "$cpu" "${cases[@]}" > "$out/standalone/timing.log" 2>&1
fi
for backend in Native OnnxRuntime; do
 bash "$here/run.sh" "$out/physics/$backend" "$backend" "$events" "$input" "$threads"
 bash "$here/extract.sh" "$out/physics/$backend" "$events" > "$out/physics/$backend/extract.log" 2>&1
done
for ((cycle = 1; cycle <= cycles; ++cycle)); do
 order='OnnxRuntime Native'
 if ((cycle % 2 == 0)); then order='Native OnnxRuntime'; fi
 for backend in $order; do
  taskset -c "$cpu" bash "$here/run.sh" "$out/timing/c$cycle/$backend" "$backend" "$timing_events" "$input" 0
 done
done
for stage in pre default-threshold; do
 for backend in OnnxRuntime Native; do
  if [[ $stage == pre ]]; then export NATIVE_NN_STAGE=pre NATIVE_NN_THRESHOLD=0; else export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=15000; fi
  selection=$backend
  if [[ $backend == Native ]]; then selection=Default; fi
  bash "$here/run.sh" "$out/smoke-$stage/$backend" "$selection" 2 "$input" 0
 done
done
analyze_args=()
if ((fallback)); then
 export NATIVE_NN_STAGE=post NATIVE_NN_THRESHOLD=0 NATIVE_NN_MODEL_DIR=$out/fallback-models
 bash "$here/run.sh" "$out/smoke-fallback/Native" Native 2 "$input" 0
else
 analyze_args+=(--no-fallback)
fi
unset NATIVE_NN_MODEL_DIR NATIVE_NN_STAGE NATIVE_NN_THRESHOLD
python3 "$here/analyze.py" "$out" --events "$events" --timing-events "$timing_events" --cycles "$cycles" "${analyze_args[@]}" > "$out/analysis.log"
if ((off_restore)); then
 bash "$here/check_off_restore.sh" "$out" > "$out/off-restore.log" 2>&1
fi
printf 'CAMPAIGN COMPLETE\n'
