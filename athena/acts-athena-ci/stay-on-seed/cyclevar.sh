#!/bin/bash
# Serial CPU cycles over seed-estimation variants (default RDO), alternating, idle-gated.
# usage: cyclevar.sh <tag> <ncycles> <nevents> <variant>...
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NCYC=$2; NEV=$3; shift 3
R=$A/run/stay-on-seed/$TAG; mkdir -p $R; cd $R
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
for i in $(seq 1 $NCYC); do
  for n in "$@"; do
    c=$(cfgof $n) || { echo "bad variant $n"; exit 1; }; force=${c%%|*}; attrs=${c#*|}
    d=${n}_$i; rm -rf $d; mkdir -p $d
    while [ $(cut -d. -f1 /proc/loadavg) -gt ${MAX_LOAD:-3} ]; do sleep 30; done
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source ${BUILD:-$A/athena-build-mr92381-base}/x86_64-el9-gcc15-opt/setup.sh && \
      EXTRA_PRE="flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$(tpe "$attrs")" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 1 $NEV serial )
  done
done
echo CYCLEVAR_DONE_$TAG
