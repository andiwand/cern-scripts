#!/bin/zsh
# intermediate baseline cuts: physics, then timing interleaved with the anchors
source ~/cern/source/acts/acts/dev3/activate.sh >/dev/null 2>&1 || true
RUNS=${1:?runs dir}
TIMING=${2:?timing dir}
cd ${0:a:h}
for c in "base25 25 50" "base35 35 70"; do
  set -- ${=c}
  python run.py -o $RUNS/$1 -n 200 -j 6 --mode 0 --chi2 $2 $3 > $RUNS/$1.log 2>&1
  echo "$(date +%T) physics $1"
done
for r in 4 5; do
  for c in "base15 15 25" "base25 25 50" "base35 35 70" "base49 49 100"; do
    set -- ${=c}
    python run.py -o $TIMING/$1_r$r -n 20 -j 1 --mode 0 --chi2 $2 $3 --no-writers > $TIMING/$1_r$r.log 2>&1
    echo "$(date +%T) round $r $1 $(grep TrackFindingAlgorithm $TIMING/$1_r$r/timing.csv | cut -d, -f3)"
  done
done
