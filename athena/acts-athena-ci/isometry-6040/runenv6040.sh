#!/bin/bash
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,main,2026-09-15T2100,gcc15"
source $ACI_BASE/athena-build-6040/x86_64-el9-gcc15-opt/setup.sh
