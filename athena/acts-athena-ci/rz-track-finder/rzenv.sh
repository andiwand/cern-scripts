#!/bin/bash
# Build environment for the RZ track finder Athena integration
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
export ATHENA_SOURCE=$ACI_BASE/athena-rz
export ACTS_SOURCE=$ACI_BASE/acts-rz
export LCG_PLATFORM=x86_64-el9-gcc15-opt
export COMPILER=gcc15
export ATHENA_RELEASE=main
export RZ_NIGHTLY=${RZ_NIGHTLY:-2026-09-04T2100}
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,${ATHENA_RELEASE},${RZ_NIGHTLY},${COMPILER}"
