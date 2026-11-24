#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/env.sh > /tmp/native-pixel-nn-env.log 2>&1
set -e
native_build=/home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn
mkdir -p "$native_build"
cd "$native_build"
cmake /home/astefl/source/acts/acts-athena-ci/athena-native-pixel-nn/Projects/WorkDir -GNinja \
 -DCMAKE_MAKE_PROGRAM="$(command -v ninja)" \
 -DATLAS_PACKAGE_FILTER_FILE=/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/package_filter.txt \
 -DCMAKE_CXX_COMPILER_LAUNCHER="$(command -v ccache)" \
 -DSICLUSTERIZATION_NATIVE_NN_AVX2=ON "$@" > configure.log 2>&1
rg -m1 'Package filtering rules read' configure.log
cmake --build . -- -j 8 > build.log 2>&1
