#!/bin/bash
# Geant4-refitted tail model: reco g5 g4 g35, redo failures, IDPVM one variant at a time.
S=~/scripts/athena/acts-athena-ci/scattering-tail
JOBS=6 bash $S/redo4.sh g5 g4 g35
JOBS=6 bash $S/redo4.sh g5 g4 g35
for v in g5 g4 g35; do SETS="hs all" bash ~/scripts/athena/acts-athena-ci/common/idpvm.sh scattering-tail $v; done
echo QUEUE6_DONE
