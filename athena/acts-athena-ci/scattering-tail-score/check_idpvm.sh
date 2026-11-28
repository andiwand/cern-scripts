#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source /home/astefl/source/acts/acts-athena-ci/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh
set -e
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score/pilot
mkdir "$SCORE_RUN/idpvm"
cd "$SCORE_RUN/idpvm"
runIDPVM.py --filesInput "$SCORE_RUN/core7_on/myAOD.pool.root" --outputFile idpvm.root \
  --OnlyTrackingPreInclude --doDuplicate --HSFlag All > idpvm.log 2>&1
