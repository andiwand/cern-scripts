#!/bin/bash
# Configure (once, or again with CFG=1) and build a study's Athena worktree against its nightly.
# usage: build.sh <study> [<flavour>]     env: NJ (parallel jobs, default 16), CFG=1 (reconfigure)
# The study's env.sh sets NIGHTLY_NAME and:
#   BUILD_SRC   Athena worktree under $ACI_BASE (e.g. athena-edgehole)
#   BUILD_DIR   build directory under $ACI_BASE (e.g. athena-build-edgehole)
#   BUILD_ARGS  extra cmake arguments (optional, e.g. -DATLAS_ACTS_SOURCE_DIR=...)
# The package filter is <study>/package_filter.txt.
# A flavour is a second build of the same worktree: directory $BUILD_DIR-<flavour>,
# filter <study>/package_filter_<flavour>.txt, cmake arguments $BUILD_ARGS_<flavour>.
S=~/scripts/athena/acts-athena-ci/$1; FL=$2
source $S/env.sh || exit 1
: "${BUILD_SRC:?not set in $S/env.sh}" "${BUILD_DIR:?not set in $S/env.sh}"
F=$S/package_filter.txt
if [ -n "$FL" ]; then BUILD_DIR=$BUILD_DIR-$FL; F=$S/package_filter_$FL.txt; v=BUILD_ARGS_$FL; BUILD_ARGS=${!v}; fi
B=$ACI_BASE/$BUILD_DIR
mkdir -p $B && cd $B || exit 1
if [ ! -f build.ninja ] || [ "${CFG:-0}" = 1 ]; then
  cmake $ACI_BASE/$BUILD_SRC/Projects/WorkDir -GNinja -DCMAKE_MAKE_PROGRAM="$(which ninja)" \
    -DATLAS_PACKAGE_FILTER_FILE=$F \
    -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) $BUILD_ARGS > cfg.log 2>&1 || { echo CFG FAIL; exit 1; }
  grep -m1 "Package filtering rules read" cfg.log; grep -m1 "Using ACTS from" cfg.log
fi
cmake --build . -- -j ${NJ:-16} > build.log 2>&1; echo "BUILD RC=$?"
