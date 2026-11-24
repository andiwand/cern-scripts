#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-study-athena-env.log 2>&1
set -e
nn_build=/home/astefl/source/acts/acts-athena-ci/athena-build-nn-inference
mkdir -p "$nn_build"
cd "$nn_build"
cmake /home/astefl/source/acts/acts-athena-ci/athena-nn-inference/Projects/WorkDir -GNinja \
 -DCMAKE_MAKE_PROGRAM="$(command -v ninja)" \
 -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/nn-inference/fixtures/package_filter.txt \
 -DCMAKE_CXX_COMPILER_LAUNCHER="$(command -v ccache)" > configure.log 2>&1
rg -m1 'Package filtering rules read' configure.log
cmake --build . -- -j 8 > build.log 2>&1
ctest --output-on-failure -R '^ActsTrackReconstruction_' > tests.log 2>&1
cat tests.log
