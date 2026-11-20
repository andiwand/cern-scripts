#!/bin/bash
# Serial CPU, alternating variants of run.sh in one build: run/strip-branching/<tag>/c<i>/<variant>
# usage: cycle.sh <tag> <ncycles> <nevents> <variant>...
TAG=$1; NCYC=$2; NEV=$3; shift 3
cd ~/scripts/athena/acts-athena-ci/strip-branching
for i in $(seq 1 $NCYC); do
  for v in "$@"; do
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- c$i $v start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    PAR=1 MODE=serial ./run.sh $TAG/c$i 1 $NEV $v | grep RECO
  done
done
echo CYCLE_DONE_$TAG
