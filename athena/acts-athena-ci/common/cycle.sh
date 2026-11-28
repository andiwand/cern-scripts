#!/bin/bash
# Serial CPU, alternating variants of a study's run.sh in one build: run/<study>/<tag>/c<i>/<variant>
# usage: cycle.sh <study> <tag> <ncycles> <nevents> <variant>...   env: MAX_LOAD (wait while load is above, default 3), RUN (default run.sh)
STUDY=$1; TAG=$2; NCYC=$3; NEV=$4; shift 4
cd ~/scripts/athena/acts-athena-ci/$STUDY || exit 1
for i in $(seq 1 $NCYC); do
  for v in "$@"; do
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- c$i $v start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    PAR=1 MODE=serial ./${RUN:-run.sh} $TAG/c$i 1 $NEV $v | grep RECO
  done
done
echo CYCLE_DONE_$TAG
