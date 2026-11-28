#!/bin/bash
source /home/astefl/source/acts/acts-athena-ci/studies/strip-seeding-20261126/env.sh
set -e
mkdir -p "$ACI_BASE/athena-build-strip-seeding"
cd "$ACI_BASE/athena-build-strip-seeding"
cmake "$ACI_BASE/athena-strip-seeding/Projects/WorkDir" -GNinja \
  -DCMAKE_MAKE_PROGRAM="$(which ninja)" -DCMAKE_CXX_COMPILER_LAUNCHER="$(which ccache)" \
  -DATLAS_PACKAGE_FILTER_FILE="$STRIP_STUDY/package_filter.txt" > configure.log 2>&1
rg 'Package filtering rules read|packages' configure.log | tail -4
cmake --build . -- -j 16 > build.log 2>&1
