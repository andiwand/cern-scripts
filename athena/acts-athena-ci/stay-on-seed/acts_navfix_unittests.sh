#!/bin/bash
# Standalone ACTS core unit tests for the acts/ checkout (navigator fix branch) (propagator/navigator subset).
source /home/astefl/source/acts/acts-athena-ci/env.sh >/dev/null 2>&1
B=/home/astefl/source/acts/acts-athena-ci/acts-navfix-unittest-build
mkdir -p $B && cd $B
[ -f build.ninja ] || cmake /home/astefl/source/acts/acts-athena-ci/acts -GNinja -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER_LAUNCHER=$(which ccache) -DACTS_BUILD_UNITTESTS=ON -DACTS_BUILD_INTEGRATIONTESTS=ON \
  -DBoost_DIR=$(grep ^Boost_DIR: /home/astefl/source/acts/acts-athena-ci/athena-build/CMakeCache.txt | cut -d= -f2) \
  -DEigen3_DIR=$(grep ^Eigen3_DIR: /home/astefl/source/acts/acts-athena-ci/athena-build/CMakeCache.txt | cut -d= -f2) > cfg.log 2>&1 || { tail -20 cfg.log; exit 1; }
T=$(ninja -t targets all | grep -oE '^Acts(UnitTest|IntegrationTest)[A-Za-z]*(Propagat|Navigat|MultiStepper|CovarianceEngine|ImpactPoint|KalmanFitter|Gsf|CombinatorialKalman|TrackHelper|Vertex)[A-Za-z]*:' | tr -d : | sort -u)
echo "targets:" $T
ninja -j ${JOBS:-24} $T > build.log 2>&1 || { grep -E 'error|FAILED' build.log | head -20; exit 1; }
R=$(echo $T | sed 's/ActsUnitTest//g; s/ActsIntegrationTest//g; s/ /|/g')
ctest -R "^(UnitTest|IntegrationTest)?($R)\$" -j 8 --output-on-failure > ctest.log 2>&1
echo "CTEST_RC=$?"; grep -E 'tests passed|Failed|\*\*\*' ctest.log | head -30
