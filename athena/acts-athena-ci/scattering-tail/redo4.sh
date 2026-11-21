#!/bin/bash
# Re-run every (file, variant) whose log.RAWtoALL does not end successfully. usage: redo.sh <variant>...  env JOBS (default 6)
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail; I=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input
for v in "$@"; do for f in $(ls $I/RDO.*); do n=$(basename $f | grep -o '\._0000[0-9]*' | tail -c3)
  grep -q 'leaving with code 0' $R/f$n/$v/log.RAWtoALL 2>/dev/null || echo "$v $f $n"; done; done |
  xargs -P ${JOBS:-6} -L1 bash -c 'INPUT_RDO=$1 PAR=1 bash ~/scripts/athena/acts-athena-ci/scattering-tail/run4.sh f$2 8 -1 $0 | grep RECO'
echo REDO_DONE
