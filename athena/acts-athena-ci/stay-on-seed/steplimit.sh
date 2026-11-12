#!/bin/bash
# CPU with maxPropagationStep=1000 on the primary finder, fwd and reverse, MR 92380 build, serial 20 ev, alternating 2 cycles
A=/home/astefl/source/acts/acts-athena-ci; D=~/scripts/athena/acts-athena-ci/mr92381
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
R=$A/run/stay-on-seed/steplimit; mkdir -p $R
LIM="${LIM-cfg.getEventAlgo('ActsTrackFindingAlg').maxPropagationStep=1000;}"
for i in 1 2; do for n in ${NAMES:-fwd-lim revs-lim}; do
  extra=""; [ $n = revs-lim ] && extra="$REVSPOST"; [ $n = revsb2 ] && extra="$REVSPOST$(tpe "{'bFieldMode': 2}")"; [ $n = fwd ] && extra=""
  while [ $(cut -d. -f1 /proc/loadavg) -gt 3 ]; do sleep 20; done
  rm -rf $R/${n}_$i; mkdir -p $R/${n}_$i
  ( cd $R/${n}_$i && source $D/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="flags.Acts.forceTrackOnSeed=True;" EXTRA_POST="$extra$LIM" bash $D/spotjob.sh 1 20 serial | sed "s/^/${n}_$i /" )
done; done; echo STEPLIMIT_DONE
