#!/bin/bash
# Build environment for the GBTS strip seeding work (Athena main + ACTS main)
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
export ATHENA_SOURCE=$ACI_BASE/athena
export ACTS_SOURCE=$ACI_BASE/acts
export GBTS_BUILD=$ACI_BASE/athena-build-gbts
export LCG_PLATFORM=x86_64-el9-gcc15-opt
export COMPILER=gcc15
export ATHENA_RELEASE=main
export GBTS_NIGHTLY=${GBTS_NIGHTLY:-2026-09-02T2100}
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,${ATHENA_RELEASE},${GBTS_NIGHTLY},${COMPILER}"
