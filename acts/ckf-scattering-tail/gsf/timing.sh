#!/bin/zsh
# CKF time of the GSF study: the six configs of a round run concurrently,
# single thread each (6 performance cores), median of per-round ratios later
D=${0:a:h}
OUT=${1:?output dir}; ROUNDS=${2:-3}
. $D/env.sh >/dev/null 2>&1
. ~/cern/build/acts/acts/ckf-tail-main/this_acts_withdeps.sh
export PYTHONPATH=~/cern/source/acts/acts/ckf-tail-main/Examples/Scripts/Python:$PYTHONPATH
export ACTS_SOURCE=~/cern/source/acts/acts/ckf-tail-main
cd $D; mkdir -p $OUT
typeset -A args
args=(base15 "" tail15 "--tail" fi_base15 "--full-inward" fi_tail15 "--full-inward --tail" fi_gsf4 "--full-inward --mixture 4" fi_gsf8 "--full-inward --mixture 8")
names=(base15 tail15 fi_base15 fi_tail15 fi_gsf4 fi_gsf8)
for r in $(seq 1 $ROUNDS); do
  for c in $names; do
    python run_main.py -o $OUT/${c}_r$r -n 20 -j 1 --no-writers ${=args[$c]} > $OUT/${c}_r$r.log 2>&1 &
  done
  wait
  echo "round $r $(for c in $names; do echo -n "$c=$(grep TrackFindingAlgorithm $OUT/${c}_r$r/timing.csv | cut -d, -f3) "; done)"
done
