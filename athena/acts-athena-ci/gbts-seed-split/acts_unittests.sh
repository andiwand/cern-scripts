#!/bin/bash
# ACTS seeding unit tests for acts-pr/ (branch gbts-remove-seed-split)
source /home/astefl/scripts/athena/acts-athena-ci/gbts-seed-split/env.sh >/dev/null 2>&1
B=/home/astefl/source/acts/acts-athena-ci/acts-pr-unittest-build
mkdir -p $B && cd $B
[ -f build.ninja ] || cmake /home/astefl/source/acts/acts-athena-ci/acts-pr -GNinja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) -DACTS_BUILD_UNITTESTS=ON \
  -DBoost_DIR=$(grep ^Boost_DIR: /home/astefl/source/acts/acts-athena-ci/acts-unittest-build/CMakeCache.txt | cut -d= -f2) \
  -DEigen3_DIR=$(grep ^Eigen3_DIR: /home/astefl/source/acts/acts-athena-ci/acts-unittest-build/CMakeCache.txt | cut -d= -f2) > cfg.log 2>&1 || { tail -20 cfg.log; exit 1; }
T=$(ninja -t targets all | grep -oE '^ActsUnitTest[A-Za-z]*(Gbts|Seed)[A-Za-z]*:' | tr -d : | sort -u)
echo "targets:" $T
ninja -j ${JOBS:-24} $T > build.log 2>&1 || { grep -E 'error|FAILED' build.log | head -20; exit 1; }
R=$(echo $T | sed 's/ActsUnitTest//g; s/ /|/g')
ctest -R "^(UnitTest)?($R)\$" -j 8 --output-on-failure > ctest.log 2>&1
echo "CTEST_RC=$?"; grep -E 'tests passed|Failed|\*\*\*|error' ctest.log | head -30
