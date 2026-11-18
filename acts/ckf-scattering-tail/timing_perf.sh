#!/bin/zsh
# single-thread CKF timing of the mixture CPU fixes, configs interleaved
source ${0:a:h}/activate-perf.sh >/dev/null 2>&1 || true
OUT=${1:?output dir}
N=${2:-20}
ROUNDS=${3:-3}
cd ${0:a:h}
# name mode chi2meas chi2out opt
# CONFIGS="name mode c1 c2 opt;..." overrides the list
configs=(
  "base15 0 15 25 0"
  "base25 0 25 50 0"
  "mix15 4 15 25 0"
  "mix15o1 4 15 25 1"
  "mix15o5 4 15 25 5"
  "mix15o13 4 15 25 13"
  "mix15o15 4 15 25 15"
  "mix15o31 4 15 25 31"
)
[[ -n $CONFIGS ]] && configs=("${(@s:;:)CONFIGS}")
mkdir -p $OUT
for r in $(seq 1 $ROUNDS); do
  for c in $configs; do
    set -- ${=c}
    python run.py -o $OUT/$1_r$r -n $N -j 1 --mode $2 --chi2 $3 $4 --opt $5 --rgate 0.05 --no-writers > $OUT/$1_r$r.log 2>&1
    echo "$(date +%T) round $r $1 $(grep TrackFindingAlgorithm $OUT/$1_r$r/timing.csv | cut -d, -f3)"
  done
done
