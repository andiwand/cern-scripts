#!/bin/bash
# Alternate forceTrackOnSeed on/off serially in one build (base: main + ACTS 48.5.0)
# usage: cycle.sh <tag> <ncycles> <nevents>    env: BUILD, EXTRA_PRE_COMMON, START
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NCYC=$2; NEV=$3; B=${BUILD:-$A/athena-build-mr92381-base}
R=$A/run/stay-on-seed/$TAG; mkdir -p $R; cd $R
for i in $(seq ${START:-1} $((${START:-1} + NCYC - 1))); do
  for side in on off; do
    d=${side}_$i; rm -rf $d; mkdir -p $d
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    PRE="flags.Acts.forceTrackOnSeed=$( [ $side = on ] && echo True || echo False );${EXTRA_PRE_COMMON}"
    ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $B/x86_64-el9-gcc15-opt/setup.sh && \
      EXTRA_PRE="$PRE" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 1 $NEV serial )
    echo "--- $d done $(date +%T)"
  done
done
echo CYCLE_DONE_$TAG
