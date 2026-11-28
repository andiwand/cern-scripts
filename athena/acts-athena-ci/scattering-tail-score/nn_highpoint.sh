#!/bin/bash
S=/home/astefl/scripts/athena/acts-athena-ci/scattering-tail-score
R=/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
set -e
trap 'echo $? > "$R/nn-extended/highpoint-exit-code"' EXIT
for p in "$R/nn-native/validation/tail5" "$R/nn-extended/validation/core14"; do
  while [[ ! -f "$p/exit-code" ]]; do sleep 30; done
  [[ $(cat "$p/exit-code") == 0 ]]
done
python "$S/cross_nn.py" "$R" nn-extended 0.998
