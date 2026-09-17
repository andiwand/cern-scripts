#!/bin/bash
# Environment for the PR 6040 (Transform3 Isometry) Athena integration test
export ATLAS_LOCAL_ROOT_BASE=/cvmfs/atlas.cern.ch/repo/ATLASLocalRootBase
export ACI_BASE=/home/astefl/source/acts/acts-athena-ci
export ATHENA_SOURCE=$ACI_BASE/athena-6040
export ACTS_SOURCE=$ACI_BASE/acts-6040
export NIGHTLY_NAME=${NIGHTLY_NAME:-2026-09-15T2100}
source ${ATLAS_LOCAL_ROOT_BASE}/user/atlasLocalSetup.sh --quiet
asetup "Athena,main,${NIGHTLY_NAME},gcc15"
