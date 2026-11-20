#!/bin/bash
# Build ActsConfig from athena-edgehole against the nightly (python only).
source ~/scripts/athena/acts-athena-ci/edge-holes/env.sh
B=$ACI_BASE/athena-build-edgehole
mkdir -p $B && cd $B || exit 1
cmake $ACI_BASE/athena-edgehole/Projects/WorkDir -GNinja -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
  -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/edge-holes/package_filter.txt \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) > cfg.log 2>&1 || { echo CFG FAIL; exit 1; }
grep -m1 "Package filtering rules read" cfg.log
cmake --build . -- -j 16 > build.log 2>&1; echo "BUILD RC=$?"
