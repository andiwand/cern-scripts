#!/usr/bin/env bash
# Interleaved A/B timing of two ACTS clones with full_chain_perf.py.
#
#   ab.sh BASE CHANGED [full_chain_perf.py options]
#
# BASE and CHANGED name clones in ~/cern/source/acts/acts with a build of the
# same name in ~/cern/build/acts/acts and an activate.sh in the clone. Each
# round runs BASE then CHANGED into $OUT/main_<i> and $OUT/changed_<i>; compare
# with compare_ab.py $OUT. Without options it runs
# `--ttbar --runs 8 --events 3` (CKF stage).
#
# Environment: OUT (default ~/cern/data/benchmark/ab_<BASE>_<CHANGED>),
# ROUNDS (default 4), plus the CKF_* variables of full_chain_perf.py
# (CKF_RECORD_MATERIAL_STATES defaults to 0 here).
# NOTE: no `set -u` -- activate.sh expands an unset PYTHONPATH and would abort.
set -eo pipefail

if [ $# -lt 2 ]; then
  sed -n '2,13p' "$0"
  exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
FULL_CHAIN=$SCRIPT_DIR/full_chain_perf.py

BASE=$1
CHANGED=$2
shift 2
if [ $# -eq 0 ]; then
  set -- --ttbar --runs 8 --events 3
fi

OUT=${OUT:-$HOME/cern/data/benchmark/ab_${BASE}_${CHANGED}}
ROUNDS=${ROUNDS:-4}
export CKF_RECORD_MATERIAL_STATES=${CKF_RECORD_MATERIAL_STATES:-0}

run_side() {
  local name=$1 dir=$2
  shift 2
  mkdir -p "$dir"
  (
    . "$HOME/cern/source/acts/acts/$name/activate.sh" > /dev/null 2>&1
    python3 -c "import acts; print('acts from', acts.__file__)"
    python3 -u "$FULL_CHAIN" "$dir" "$@"
  ) > "$dir/log.txt" 2>&1
  grep -q "^acts from $HOME/cern/build/acts/acts/$name/" "$dir/log.txt" \
    || { echo "WRONG acts for $name in $dir"; exit 1; }
}

for i in $(seq 1 "$ROUNDS"); do
  echo "round $i: main ($BASE)"
  run_side "$BASE" "$OUT/main_$i" "$@"
  echo "round $i: changed ($CHANGED)"
  run_side "$CHANGED" "$OUT/changed_$i" "$@"
done
echo "done -> $OUT"
