#!/bin/bash
# Build environment for the RZ track finder on ACTS v47.7.0 (feat-rz-track-finder
# carried onto the pin) and Athena rz-finder-v47.7, nightly 2026-09-15T2100
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
export ATHENA_SOURCE=$ACI_BASE/athena-rz2
export ACTS_SOURCE=$ACI_BASE/acts-rz2
export LCG_PLATFORM=x86_64-el9-gcc15-opt
export COMPILER=gcc15
export ATHENA_RELEASE=main
export RZ_NIGHTLY=${RZ2_NIGHTLY:-2026-09-15T2100}
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,${ATHENA_RELEASE},${RZ_NIGHTLY},${COMPILER}"
