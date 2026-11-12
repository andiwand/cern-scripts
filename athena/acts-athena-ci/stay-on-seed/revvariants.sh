#!/bin/bash
# Reverse-search variants on the primary pass, MR 92380 build, full-truth 3 files, MT8.
# usage: revvariants.sh <rev-|fwd-><variant>...   e.g. rev-on rev-off-all-p3s2 fwd-on (fwd = MR build, no reverse)
A=/home/astefl/source/acts/acts-athena-ci
E=${SOS_INPUT:-/home/astefl/source/acts/acts-athena-ci/run/stay-on-seed/input}   # local copy of /eos/atlas/atlascerngroupdisk/perf-idtracking/GNN4ITk/EFT/ttbar_EFT_RDOFiles
export INPUT_RDO=$E/RDO.39626672._000001.pool.root.1,$E/RDO.39626672._000003.pool.root.1,$E/RDO.39626672._000004.pool.root.1
R=$A/run/stay-on-seed/variants; mkdir -p $R
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
run() {
  local n=$1 dir=${1%%-*} base=${1#*-} c
  c=$(cfgof $base) || { echo "bad variant $n"; return; }
  local force=${c%%|*} attrs=${c#*|} extra=""
  [ $dir = rev ] && extra="$REVPOST"; [ $dir = revs ] && extra="$REVSPOST"
  d=$R/$n; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-mr92380/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$(tpe "$attrs")$extra" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 8 300 mt | sed "s/^/$n /" )
}
i=0
for n in "$@"; do run $n & i=$((i+1)); [ $((i % ${PAR:-4})) -eq 0 ] && wait; done
wait; echo REVVARIANTS_DONE
