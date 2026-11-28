#!/bin/bash
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source /home/astefl/source/acts/acts-athena-ci/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh
set -e
SCORE_RUN=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score/nn-extended
SCORE_SCRIPTS=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
trap 'echo $? > "$SCORE_RUN/extras-exit-code"' EXIT
python "$SCORE_SCRIPTS/extras.py" "$SCORE_RUN/validation/core10/myAOD.pool.root" "$SCORE_RUN/validation/core10/extras.tsv" > "$SCORE_RUN/validation/core10/extras.log" 2>&1 &
score_core_pid=$!
python "$SCORE_SCRIPTS/extras.py" "$SCORE_RUN/validation/tail5/myAOD.pool.root" "$SCORE_RUN/validation/tail5/extras.tsv" > "$SCORE_RUN/validation/tail5/extras.log" 2>&1 &
score_tail_pid=$!
wait "$score_core_pid"
wait "$score_tail_pid"

python "$SCORE_SCRIPTS/why.py" "$SCORE_RUN" > "$SCORE_RUN/why.log" 2>&1
