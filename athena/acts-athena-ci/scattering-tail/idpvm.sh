#!/bin/bash
# IDPVM over the AODs of several run tags: run/edge-holes/ana/<v>/idpvm_hs.root (hard-scatter truth), idpvm_all.root (HS + pile-up).
# usage: idpvm.sh <variant>...   env: RUNS (run tags, default "perf perf2"), SETS (default "hs all"; "lrt" = HS + PU truth
#        with --doLargeD0Tracks, InDetLargeD0TrackParticles -> idpvm_lrt.root)
source ~/scripts/athena/acts-athena-ci/scattering-tail/env.sh
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail
for v in "$@"; do
  mkdir -p $R/ana/$v; in=$(for t in ${RUNS:-$(cd $R && ls -d f[0-9]* | paste -sd" ")}; do echo $R/$t/$v/myAOD.pool.root; done | paste -sd,)
  for s in ${SETS:-hs all}; do
    f=HardScatter; x=""; [ $s != hs ] && f=All; [ $s = lrt ] && x="--doLargeD0Tracks"
    ( cd $R/ana/$v && runIDPVM.py --filesInput $in --outputFile idpvm_$s.root --OnlyTrackingPreInclude \
        --doDuplicate --HSFlag $f $x > idpvm_$s.log 2>&1; echo "$v $s rc=$?" ) &
  done
done
wait
