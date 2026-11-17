#!/bin/bash
# Serial CPU A/B, split on/off alternating in one build, default RUN4 RDO.
# usage: cycle.sh <tag> <ncycles> <nevents>
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NCYC=$2; NEV=$3
R=$A/run/gbts-seed-split/$TAG; mkdir -p $R; cd $R
T="cfg.getEventAlgo('ActsPixelSeedingAlg').SeedTool"
for i in $(seq 1 $NCYC); do
  for side in on off; do
    d=${side}_$i; rm -rf $d; mkdir -p $d
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    P=""; [ $side = off ] && P="$T.maxSeedSplitEta=0.0;"
    ( cd $d && source ~/scripts/athena/acts-athena-ci/gbts-seed-split/env.sh && source $A/athena-build-gbtssplit/x86_64-el9-gcc15-opt/setup.sh >/dev/null 2>&1 && \
      EXTRA_POST="$P" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 1 $NEV serial )
  done
done
echo CYCLE_DONE_$TAG
