#!/bin/bash
# Standalone ACTS unit (and integration) tests of one ACTS tree, the subset whose names match a pattern.
# usage: acts_unittests.sh <acts tree under $ACI_BASE> <name regex>   e.g. acts-tail 'CombinatorialKalman|MeasurementSelector|Gsf'
# env: STUDY (source <study>/env.sh instead of the checkout's env.sh), INTEGRATION=1 (also integration tests),
#      CACHE (CMakeCache.txt to take Boost_DIR / Eigen3_DIR from, default $ACI_BASE/athena-build/CMakeCache.txt), JOBS (default 24)
# Build directory: $ACI_BASE/<tree>-unittest-build (configured once).
TREE=$1; PAT=$2
if [ -n "$STUDY" ]; then source ~/scripts/athena/acts-athena-ci/$STUDY/env.sh >/dev/null 2>&1
else source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1; fi
A=/home/astefl/source/acts/acts-athena-ci; C=${CACHE:-$A/athena-build/CMakeCache.txt}
B=$A/$TREE-unittest-build
mkdir -p $B && cd $B || exit 1
IT=OFF; [ "${INTEGRATION:-0}" = 1 ] && IT=ON
[ -f build.ninja ] || cmake $A/$TREE -GNinja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) -DACTS_BUILD_UNITTESTS=ON -DACTS_BUILD_INTEGRATIONTESTS=$IT \
  -DBoost_DIR=$(grep ^Boost_DIR: $C | cut -d= -f2) \
  -DEigen3_DIR=$(grep ^Eigen3_DIR: $C | cut -d= -f2) > cfg.log 2>&1 || { tail -20 cfg.log; exit 1; }
T=$(ninja -t targets all | grep -oE "^Acts(UnitTest|IntegrationTest)[A-Za-z]*($PAT)[A-Za-z]*:" | tr -d : | sort -u)
echo "targets:" $T
ninja -j ${JOBS:-24} $T > build.log 2>&1 || { grep -E 'error|FAILED' build.log | head -20; exit 1; }
R=$(echo $T | sed 's/ActsUnitTest//g; s/ActsIntegrationTest//g; s/ /|/g')
ctest -R "^(UnitTest|IntegrationTest)?($R)\$" -j 8 --output-on-failure > ctest.log 2>&1
echo "CTEST_RC=$?"; grep -E 'tests passed|Failed|\*\*\*|error' ctest.log | head -30
