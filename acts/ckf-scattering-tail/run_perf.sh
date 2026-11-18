#!/bin/zsh
# physics runs of the mixture CPU fixes: name mode chi2meas chi2out opt
source ${0:a:h}/activate-perf.sh >/dev/null 2>&1 || true
OUT=${1:?output dir}
N=${2:-200}
cd ${0:a:h}
mkdir -p $OUT
python run.py -o $OUT/truth -n $N -j 6 --truth-only > $OUT/truth.log 2>&1
configs=(
  "base15 0 15 25 0"
  "base25 0 25 50 0"
  "mix15 4 15 25 0"
  "mix15o111 4 15 25 111"
  "mix15o31 4 15 25 31"
)
first=1
for c in $configs; do
  set -- ${=c}
  extra=()
  if [[ $first == 1 ]]; then extra=(--record-scatters); first=0; fi
  echo "$(date +%T) start $1"
  python run.py -o $OUT/$1 -n $N -j 6 --mode $2 --chi2 $3 $4 --opt $5 --rgate 0.05 $extra > $OUT/$1.log 2>&1
  echo "$(date +%T) done $1 $(grep -o 'scattering tail: [0-9]*' $OUT/$1.log)"
done
