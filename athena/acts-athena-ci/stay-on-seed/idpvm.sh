#!/bin/bash
# usage: idpvm.sh <dir-with-myAOD>
cd $1 && source ~/scripts/athena/acts-athena-ci/mr92381/env.sh >/dev/null 2>&1 && \
runIDPVM.py --filesInput myAOD.pool.root --outputFile idpvm.root --OnlyTrackingPreInclude --doExpertPlots --doDuplicate > idpvm.log 2>&1
echo "IDPVM RC=$? $1"
