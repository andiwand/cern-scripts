#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
SCORE_BASE=/home/astefl/source/acts/acts-athena-ci
SCORE_BUILD=$SCORE_BASE/athena-build-tail-score
SCORE_TEST=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score/test_scorer.cxx
SCORE_EIGEN=$(sed -n 's/^EIGEN_INCLUDE_DIR:PATH=//p' "$SCORE_BUILD/CMakeCache.txt")
g++ -std=c++23 -O1 -UNDEBUG -I"$SCORE_BASE/acts-tail-score/Core/include" \
  -I"$SCORE_BUILD/x86_64-el9-gcc15-opt/include" -I"$SCORE_EIGEN" \
  -I"$SCORE_BASE/athena-tail-score/Tracking/Acts/ActsTrackReconstruction/src" \
  "$SCORE_TEST" -L"$SCORE_BUILD/x86_64-el9-gcc15-opt/lib" \
  -Wl,-rpath,"$SCORE_BUILD/x86_64-el9-gcc15-opt/lib" -lActsCore \
  -o "$SCORE_BUILD/test_scorer"
"$SCORE_BUILD/test_scorer"
