#!/bin/bash
set -e
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score/pilot
SCORE_SCRIPT=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score/run.sh
mkdir "$SCORE_RUN"
for variant in tail5 core7; do
  bash "$SCORE_SCRIPT" "$SCORE_RUN/${variant}_on" "$variant" 5 0 4 1 > "$SCORE_RUN/${variant}_on.driver.log" 2>&1 &
  score_on_pid=$!
  bash "$SCORE_SCRIPT" "$SCORE_RUN/${variant}_off" "$variant" 5 0 4 0 > "$SCORE_RUN/${variant}_off.driver.log" 2>&1 &
  score_off_pid=$!
  wait "$score_on_pid"
  wait "$score_off_pid"
done
