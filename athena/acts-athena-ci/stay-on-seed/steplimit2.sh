#!/bin/bash
# Smoothing share: fwd + twoWaySmoothing, reverse without twoWaySmoothing; maxPropagationStep=1000, serial 20 ev, 2 cycles
A=/home/astefl/source/acts/acts-athena-ci; D=~/scripts/athena/acts-athena-ci/mr92381
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
R=$A/run/stay-on-seed/steplimit; mkdir -p $R
LIM="cfg.getEventAlgo('ActsTrackFindingAlg').maxPropagationStep=1000;"
for i in 1 2; do for n in fwdsm-lim revsnosm-lim; do
  case $n in fwdsm-lim) extra="cfg.getEventAlgo('ActsTrackFindingAlg').twoWaySmoothing=True;";;
             revsnosm-lim) extra="${REVSPOST}a.twoWaySmoothing=False;";; esac
  while [ $(cut -d. -f1 /proc/loadavg) -gt 3 ]; do sleep 20; done
  rm -rf $R/${n}_$i; mkdir -p $R/${n}_$i
  ( cd $R/${n}_$i && source $D/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="flags.Acts.forceTrackOnSeed=True;" EXTRA_POST="$extra$LIM" bash $D/spotjob.sh 1 20 serial )
done; done; echo STEPLIMIT2_DONE
