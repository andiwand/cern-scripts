#!/bin/bash
set -e
S=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score/nn-native-pilot
mkdir "$R"
bash "$S/run_nn_native.sh" "$R/core7" core7 5 0 4 & p1=$!
bash "$S/run_nn_native.sh" "$R/tail5" tail5 5 0 4 & p2=$!
wait "$p1"
wait "$p2"
