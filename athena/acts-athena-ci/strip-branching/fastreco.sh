#!/bin/bash
# Fast 1000-event reco: one job per input file (100 events), 8 threads, JOBS jobs at a time.
# The reco is bound by a serial part at ~1.35 s/event whatever the thread count, so many small jobs scale and big ones do not.
# usage: fastreco.sh <variant>...   -> run/strip-branching/f<NN>/<variant>; env JOBS (default 8), NT (default 8)
I=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input
for v in "$@"; do for f in $(ls $I/RDO.*); do n=$(basename $f | grep -o '\._0000[0-9]*' | tail -c3); echo "$v $f $n"; done; done |
  xargs -P ${JOBS:-8} -L1 bash -c 'INPUT_RDO=$1 PAR=1 bash ~/scripts/athena/acts-athena-ci/strip-branching/run.sh f$2 ${NT:-8} -1 $0 | grep RECO' 
echo FASTRECO_DONE
