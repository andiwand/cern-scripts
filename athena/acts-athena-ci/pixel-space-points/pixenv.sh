#!/bin/bash
# Build environment for the pixel space point performance work (MR 90483 + ACTS pixel-var branch)
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
export ATHENA_SOURCE=$ACI_BASE/athena
export ACTS_SOURCE=$ACI_BASE/acts
export LCG_PLATFORM=x86_64-el9-gcc15-opt
export COMPILER=gcc15
export ATHENA_RELEASE=main
export PIX_NIGHTLY=2026-08-27T2100
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,${ATHENA_RELEASE},${PIX_NIGHTLY},${COMPILER}"
