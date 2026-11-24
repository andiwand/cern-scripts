#!/usr/bin/env bash
# Diagnostic wall timers; excluded from the uninstrumented timing tables.
set -eo pipefail
nn_scripts=/home/astefl/scripts/athena/acts-athena-ci/nn-inference
nn_root=/home/astefl/source/acts/acts-athena-ci/run/nn-inference
nn_input=/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.39626672._000001.pool.root.1
for nn_backend in original direct_avx2 sofie_gemv; do
  nn_out="$nn_root/profiles/$nn_backend"
  export NN_STUDY_PROFILE="$nn_out/profile.jsonl"
  taskset -c 16 bash "$nn_scripts/run.sh" "$nn_out" "$nn_backend" 5 "$nn_input"
  test -s "$NN_STUDY_PROFILE"
  unset NN_STUDY_PROFILE
done
