#!/bin/bash
# Serial CPU cycles, MR 92380 build, fwd-/rev- prefixed variants (default RDO), alternating, idle-gated.
# usage: cyclerev.sh <tag> <ncycles> <nevents> <fwd-x|rev-x>...
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NCYC=$2; NEV=$3; shift 3
R=$A/run/stay-on-seed/$TAG; mkdir -p $R; cd $R
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
for i in $(seq 1 $NCYC); do
  for n in "$@"; do
    dir=${n%%-*}; base=${n#*-}; c=$(cfgof $base) || { echo "bad variant $n"; exit 1; }; force=${c%%|*}; attrs=${c#*|}
    extra=""; [ $dir = rev ] && extra="$REVPOST"; [ $dir = revs ] && extra="$REVSPOST"
    d=${n}_$i; rm -rf $d; mkdir -p $d
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh && \
      EXTRA_PRE="flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$(tpe "$attrs")$extra" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 1 $NEV serial )
  done
done
echo CYCLEREV_DONE_$TAG
