#!/bin/bash
# perf profile, primary pass only (LRT off), serial, default RDO: forcing-off FML vs forcing-off all-SP fit (or any variants)
# usage: prof.sh <nev> <variant>...
A=/home/astefl/source/acts/acts-athena-ci; D=~/scripts/athena/acts-athena-ci/mr92381
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
NEV=$1; shift; R=$A/run/stay-on-seed/prof; mkdir -p $R
for n in "$@"; do
  c=$(cfgof $n); force=${c%%|*}; attrs=${c#*|}
  rm -rf $R/$n; mkdir -p $R/$n
  while [ $(cut -d. -f1 /proc/loadavg) -gt 3 ]; do sleep 30; done
  ( cd $R/$n && source $D/env.sh && source ${BUILD:-$A/athena-build-mr92381-base}/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="flags.Acts.doLargeRadius=False;flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$(tpe "$attrs")" \
    perf record -e cycles:u -F 1999 --call-graph dwarf,32768 -m 64 -o perf.data -- bash $D/spotjob.sh 1 $NEV serial > perf.out 2>&1 )
  echo "$n profiled $(date +%T) $(grep 'RECO RC' $R/$n/perf.out)"
done
for n in "$@"; do
  ( cd $R/$n && perf script -F ip,sym -i perf.data 2>/dev/null | python3 $D/fold_tf.py > fold.txt; echo "$n folded" ) &
done
wait; echo PROF_DONE
