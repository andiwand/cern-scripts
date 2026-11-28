#!/bin/bash
# Review the completed scan and compare its main point with the raw baseline.
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_ROOT=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
trap 'echo $? > "$SCORE_ROOT/hole-scan/review-exit-code"' EXIT
while [[ ! -f "$SCORE_ROOT/hole-scan/exit-code" ]]; do sleep 10; done
[[ $(cat "$SCORE_ROOT/hole-scan/exit-code") == 0 ]]
python "$SCORE_SCRIPTS/audit_hole_scan.py" "$SCORE_ROOT/hole-scan" > "$SCORE_ROOT/hole-scan/audit.log" 2>&1
python "$SCORE_SCRIPTS/cross_nn.py" "$SCORE_ROOT" hole-scan > "$SCORE_ROOT/hole-scan/cross-calibration.log" 2>&1
