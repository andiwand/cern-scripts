#!/bin/bash
# Scattering tail (ACTS PR 6572 backported to v48.5.0 in acts-tail): nightly 2026-11-19T2100, worktree athena-tail
export NIGHTLY_NAME=2026-11-19T2100
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
# common/build.sh: athena-tail against acts-tail (ACTS inline, CPU only)
BUILD_SRC=athena-tail; BUILD_DIR=athena-build-tail; NJ=${NJ:-32}
BUILD_ARGS="-DATLAS_ACTS_SOURCE_DIR=$ACI_BASE/acts-tail -DACTS_ENABLE_CUDA=OFF -DACTS_BUILD_PLUGIN_GNN=OFF -DDETRAY_BUILD_CUDA=OFF"
# common/idpvm.sh: all full-sample tags f<i>
IDPVM_RUNS=$(cd $ACI_BASE/run/scattering-tail 2>/dev/null && ls -d f[0-9]* | paste -sd" ")
