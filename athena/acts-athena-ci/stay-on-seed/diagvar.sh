#!/bin/bash
# Instrumented (athena-sos) dump for estimation variants, full-truth file 1, MT8: run/stay-on-seed/diag-var/<variant>/sos.txt
# usage: diagvar.sh <nevents> <variant>...
A=/home/astefl/source/acts/acts-athena-ci
E=${SOS_INPUT:-/home/astefl/source/acts/acts-athena-ci/run/stay-on-seed/input}   # local copy of /eos/atlas/atlascerngroupdisk/perf-idtracking/GNN4ITk/EFT/ttbar_EFT_RDOFiles
export INPUT_RDO=$E/RDO.39626672._000001.pool.root.1
NEV=$1; shift; R=${DIAGDIR:-$A/run/stay-on-seed/diag-var}; mkdir -p $R
source ~/scripts/athena/acts-athena-ci/stay-on-seed/variant_defs.sh
TRUTH="cfg.getEventAlgo('ActsTrackFindingAlg').SosTruthMaps=['ITkPixelClustersToTruthParticles','ITkStripClustersToTruthParticles'];"
for n in "$@"; do
  c=$(cfgof $n) || { echo "bad $n"; continue; }; force=${c%%|*}; attrs=${c#*|}
  d=$R/$n; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh && source $A/athena-build-sos/x86_64-el9-gcc15-opt/setup.sh && \
    ACTS_SOS_DIAG=$d/sos.txt EXTRA_PRE="flags.Acts.forceTrackOnSeed=$force;" EXTRA_POST="$TRUTH$(tpe "$attrs")" \
    bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh 8 $NEV mt | sed "s/^/$n /" ) &
done
wait; echo DIAGVAR_DONE
