#!/bin/bash
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
python3 "$SCORE_SCRIPTS/batch.py" "$SCORE_RUN/training" 200 0 core4 core5 core7 core10 tail4 tail5 tail7 --parallel 3 || exit $?
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
python "$SCORE_SCRIPTS/analyze.py" tune "$SCORE_RUN/training" "$SCORE_RUN/training.json" > "$SCORE_RUN/tuning.log" 2>&1
