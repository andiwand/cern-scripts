#!/bin/bash
# Seed-estimation variants for the primary pass, full-truth sample, unmodified main build.
# run/stay-on-seed/variants/<name>; usage: variants.sh <name>...   (4 at a time, 8 threads each)
A=/home/astefl/source/acts/acts-athena-ci
E=${SOS_INPUT:-/home/astefl/source/acts/acts-athena-ci/run/stay-on-seed/input}   # local copy of /eos/atlas/atlascerngroupdisk/perf-idtracking/GNN4ITk/EFT/ttbar_EFT_RDOFiles
export INPUT_RDO=$E/RDO.39626672._000001.pool.root.1,$E/RDO.39626672._000003.pool.root.1,$E/RDO.39626672._000004.pool.root.1
R=${VARDIR:-$A/run/stay-on-seed/variants}; mkdir -p $R
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
run() {
  local n=$1 c; c=$(cfgof $n) || { echo "bad variant $n"; return; }
  local force=${c%%|*} attrs=${c#*|}
  d=$R/$n; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source ${BUILD:-$A/athena-build-mr92381-base}/x86_64-el9-gcc15-opt/setup.sh && \
    EXTRA_PRE="flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$(tpe "$attrs")" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 8 300 mt | sed "s/^/$n /" )
}
i=0
for n in "$@"; do run $n & i=$((i+1)); [ $((i % ${PAR:-4})) -eq 0 ] && wait; done
wait; echo VARIANTS_DONE
