#!/bin/bash
# Diagnostic run with the instrumented build: run/stay-on-seed/diag/{on,off}, MT 8 threads, writes sos.txt
# usage: diag.sh <nevents> [tag]
A=/home/astefl/source/acts/acts-athena-ci
NEV=$1; TAG=${2:-diag}; R=$A/run/stay-on-seed/$TAG; mkdir -p $R
TRUTH="cfg.getEventAlgo('ActsTrackFindingAlg').SosTruthMaps=['ITkPixelClustersToTruthParticles','ITkStripClustersToTruthParticles'];"
for side in on off; do
  d=$R/$side; rm -rf $d; mkdir -p $d
  PRE="flags.Acts.forceTrackOnSeed=$( [ $side = on ] && echo True || echo False );${EXTRA_PRE_COMMON}"
  ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-sos/x86_64-el9-gcc15-opt/setup.sh && \
    ACTS_SOS_DIAG=$d/sos.txt EXTRA_PRE="$PRE" EXTRA_POST="$TRUTH" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 8 $NEV mt ) &
done
wait; echo DIAG_DONE_$TAG
