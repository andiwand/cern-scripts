#!/usr/bin/env bash
# Interleaved A/B: BASE (baseline) vs CHANGED, CKF material states off.
# BASE and CHANGED name clones in ~/cern/source/acts/acts with a build of the
# same name in ~/cern/build/acts/acts and an activate.sh in the clone.
# NOTE: no `set -u` -- activate.sh expands an unset PYTHONPATH and would abort.
set -eo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

OUT=${OUT:-$SCRIPT_DIR/results_ab_run}
ROUNDS=${ROUNDS:-4}
BASE=${BASE:-perf1}
CHANGED=${CHANGED:-perf2}
export CKF_RUNS=${CKF_RUNS:-8}
export CKF_EVENTS=${CKF_EVENTS:-3}
export CKF_RECORD_MATERIAL_STATES=${CKF_RECORD_MATERIAL_STATES:-0}

run_side() {
  local name=$1 dir=$2
  mkdir -p "$dir"
  (
    . ~/cern/source/acts/acts/$name/activate.sh > /dev/null 2>&1
    python3 -c "import acts; print('acts from', acts.__file__)"
    python3 -u "$FULL_CHAIN" --ttbar "$dir"
  ) > "$dir/log.txt" 2>&1
  grep -q "^acts from /Users/andreas/cern/build/acts/acts/$name/" "$dir/log.txt" \
    || { echo "WRONG acts for $name in $dir"; exit 1; }
}

cd "$SCRIPT_DIR"
for i in $(seq 1 "$ROUNDS"); do
  echo "round $i: main ($BASE)"
  run_side "$BASE" "$OUT/main_$i"
  echo "round $i: changed ($CHANGED)"
  run_side "$CHANGED" "$OUT/changed_$i"
done
echo "done -> $OUT"
