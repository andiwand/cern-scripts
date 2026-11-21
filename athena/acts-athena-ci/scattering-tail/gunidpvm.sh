#!/bin/bash
# IDPVM (hard-scatter truth) over the generated AODs: run/scattering-tail/ana-mu/g<name>/<variant>/idpvm_hs.root
# usage: muidpvm.sh <sample>... (mu1|pi1|mu3|pi3)   env: VARIANTS
source ~/scripts/athena/acts-athena-ci/scattering-tail/env.sh
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail
for s in "$@"; do for v in ${VARIANTS:-t0 c35 t35 g35 c5 t5 g5 w10}; do
  o=$R/ana-mu/g$s/$v; mkdir -p $o
  ( cd $o && runIDPVM.py --filesInput $R/g$s/$v/myAOD.pool.root --outputFile idpvm_hs.root --OnlyTrackingPreInclude \
      --doDuplicate --doHitLevelPlots --HSFlag HardScatter > idpvm_hs.log 2>&1; echo "g$s $v rc=$?" ) &
done; wait; done
echo MUIDPVM_DONE
