#!/bin/bash
# Configure (once) and build athena-tail against acts-tail (ACTS inline, CPU only).
source ~/scripts/athena/acts-athena-ci/scattering-tail/env.sh
B=$ACI_BASE/athena-build-tail
mkdir -p $B && cd $B || exit 1
if [ ! -f build.ninja ]; then
cmake $ACI_BASE/athena-tail/Projects/WorkDir -GNinja -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
  -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail/package_filter.txt \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) -DATLAS_ACTS_SOURCE_DIR=$ACI_BASE/acts-tail \
  -DACTS_ENABLE_CUDA=OFF -DACTS_BUILD_PLUGIN_GNN=OFF -DDETRAY_BUILD_CUDA=OFF > cfg.log 2>&1 || { echo CFG FAIL; exit 1; }
grep -m1 "Package filtering rules read" cfg.log; grep -m1 "Using ACTS from" cfg.log
fi
cmake --build . -- -j ${NJ:-32} > build.log 2>&1; echo "BUILD RC=$?"
