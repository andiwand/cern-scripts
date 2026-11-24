#!/usr/bin/env bash
set -eo pipefail
nn_dir=$(realpath "$1");nn_events=$2
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > "$nn_dir/extract-environment.log" 2>&1
set -e
source /home/astefl/source/acts/acts-athena-ci/athena-build-nn-inference/x86_64-el9-gcc15-opt/setup.sh >> "$nn_dir/extract-environment.log" 2>&1
python3 /home/astefl/scripts/athena/acts-athena-ci/nn-inference/fixtures/outcomes.py \
 "$nn_dir/outcomes.txt.gz" "$nn_dir/myAOD.pool.root" --events "$nn_events"
