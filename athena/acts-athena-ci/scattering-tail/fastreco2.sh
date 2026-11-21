#!/bin/bash
# 1000-event reco: one job per input file (100 events), NT threads, JOBS jobs at a time -> run/scattering-tail/f<NN>/<variant>
# usage: fastreco.sh <variant>...
I=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input
for v in "$@"; do for f in $(ls $I/RDO.*); do n=$(basename $f | grep -o '\._0000[0-9]*' | tail -c3); echo "$v $f $n"; done; done |
  xargs -P ${JOBS:-8} -L1 bash -c 'INPUT_RDO=$1 PAR=1 bash ~/scripts/athena/acts-athena-ci/scattering-tail/run2.sh f$2 ${NT:-8} -1 $0 | grep RECO'
echo FASTRECO_DONE
