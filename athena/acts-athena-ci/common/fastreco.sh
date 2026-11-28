#!/bin/bash
# Fast 1000-event reco: one job per input file (100 events) -> run/<study>/f<NN>/<variant>, JOBS jobs at a time.
# The reco is bound by a serial part at ~1.35 s/event whatever the thread count, so many small jobs scale and big ones do not.
# usage: fastreco.sh <study> <variant>...   env: JOBS (default 8), NT (threads per job, default 8),
#        REDO=1 (only the (file, variant) pairs whose log.RAWtoALL did not end successfully)
STUDY=$1; shift
A=/home/astefl/source/acts/acts-athena-ci; I=$A/run/edge-holes/input
for v in "$@"; do for f in $(ls $I/RDO.*); do n=$(basename $f | grep -o '\._0000[0-9]*' | tail -c3)
  [ "${REDO:-0}" = 1 ] && grep -q 'leaving with code 0' $A/run/$STUDY/f$n/$v/log.RAWtoALL 2>/dev/null && continue
  echo "$v $f $n"; done; done |
  xargs -P ${JOBS:-8} -L1 bash -c 'INPUT_RDO=$1 PAR=1 bash ~/scripts/athena/acts-athena-ci/'$STUDY'/run.sh f$2 ${NT:-8} -1 $0 | grep RECO'
echo FASTRECO_DONE
