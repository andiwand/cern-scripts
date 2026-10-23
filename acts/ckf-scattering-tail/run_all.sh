#!/bin/zsh
# physics runs: name mode chi2meas chi2out
set -e
source ~/cern/source/acts/acts/dev3/activate.sh >/dev/null 2>&1 || true
OUT=${1:?output dir}
N=${2:-200}
cd ${0:a:h}
configs=(
  "base15 0 15 25"
  "base49 0 49 100"
  "retry15 1 15 25"
  "branch15 2 15 25"
  "selonly15 3 15 25"
  "mix15 4 15 25"
)
first=1
for c in $configs; do
  set -- ${=c}
  extra=()
  if [[ $first == 1 ]]; then extra=(--record-scatters); first=0; fi
  echo "$(date +%T) start $1"
  python run.py -o $OUT/$1 -n $N -j 6 --mode $2 --chi2 $3 $4 $extra > $OUT/$1.log 2>&1
  echo "$(date +%T) done $1 $(grep -o 'scattering tail: [0-9]*' $OUT/$1.log)"
done
