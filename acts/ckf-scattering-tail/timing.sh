#!/bin/zsh
# single-thread CKF timing, configs interleaved, rounds back to back
source ~/cern/source/acts/acts/dev3/activate.sh >/dev/null 2>&1 || true
OUT=${1:?output dir}
N=${2:-20}
ROUNDS=${3:-3}
cd ${0:a:h}
configs=(
  "base15 0 15 25"
  "base49 0 49 100"
  "retry15 1 15 25"
  "mix15 4 15 25"
  "branch15 2 15 25"
  "selonly15 3 15 25"
)
for r in $(seq 1 $ROUNDS); do
  for c in $configs; do
    set -- ${=c}
    python run.py -o $OUT/$1_r$r -n $N -j 1 --mode $2 --chi2 $3 $4 --no-writers > $OUT/$1_r$r.log 2>&1
    echo "$(date +%T) round $r $1 $(grep TrackFindingAlgorithm $OUT/$1_r$r/timing.csv | cut -d, -f3)"
  done
done
