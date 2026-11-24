#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/native-cxxutils-run-env.log 2>&1
set -euo pipefail
python3 /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/cxxutils/measure.py "$@"
