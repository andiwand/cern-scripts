#!/usr/bin/env bash
set +e
source /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/env.sh > /tmp/native-runtime-time-env.log 2>&1
set -eo pipefail
source /home/astefl/source/acts/acts-athena-ci/athena-build-native-pixel-nn/x86_64-el9-gcc15-opt/setup.sh >> /tmp/native-runtime-time-env.log 2>&1
set -u
python3 /home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/runtime/time.py
