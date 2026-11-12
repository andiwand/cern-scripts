#!/bin/bash
# Reverse-search CPU investigation, MR 92380 build, serial, default RDO.
# 1) revs-on with warning suppression off (20 ev), 2) perf of fwd-on and revs-on (10 ev, LRT off)
A=/home/astefl/source/acts/acts-athena-ci; D=~/scripts/athena/acts-athena-ci/mr92381
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
R=$A/run/stay-on-seed/revprof; mkdir -p $R
setup() { source $D/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh; }
( rm -rf $R/warn; mkdir -p $R/warn; cd $R/warn && setup && \
  EXTRA_PRE="flags.Acts.forceTrackOnSeed=True;" EXTRA_POST="${REVSPOST}cfg.getService('MessageSvc').enableSuppression=False;" \
  bash $D/spotjob.sh 1 20 serial | sed 's/^/warn /' ) &
for n in fwd-on revs-on; do
  ( rm -rf $R/$n; mkdir -p $R/$n; cd $R/$n && setup && extra=""; [ $n = revs-on ] && extra="$REVSPOST"; \
    EXTRA_PRE="flags.Acts.doLargeRadius=False;flags.Acts.forceTrackOnSeed=True;" EXTRA_POST="$extra" \
    perf record -e cycles:u -F 1999 --call-graph dwarf,32768 -m 64 -o perf.data -- bash $D/spotjob.sh 1 10 serial > perf.out 2>&1
    echo "$n profiled $(grep 'RECO RC' perf.out)"
    perf script -F ip,sym -i perf.data 2>/dev/null | python3 $D/fold_tf.py > fold.txt; echo "$n folded" ) &
done
wait; echo REVPROF_DONE
