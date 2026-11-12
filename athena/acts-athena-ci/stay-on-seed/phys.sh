#!/bin/bash
# forceTrackOnSeed A/B physics: run/stay-on-seed/<tag>/{on,off}, base build (main + ACTS 48.5.0)
# usage: phys.sh <tag> <nthreads> <nevents> [mt|serial]   env: EXTRA_PRE_ON, EXTRA_PRE_OFF
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NT=$2; NEV=$3; MODE=${4:-mt}
R=$A/run/stay-on-seed/$TAG; mkdir -p $R
for side in on off; do
  d=$R/$side; rm -rf $d; mkdir -p $d
  PRE="flags.Acts.forceTrackOnSeed=$( [ $side = on ] && echo True || echo False );"
  ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-mr92381-base/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="$PRE${EXTRA_PRE_COMMON}" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV $MODE ) &
done
wait; echo PHYS_DONE_$TAG
