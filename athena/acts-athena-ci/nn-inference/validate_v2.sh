#!/usr/bin/env bash
set -eo pipefail
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > /tmp/nn-v2-validation-env.log 2>&1
set -e
export LD_LIBRARY_PATH="$NN_STUDY_ROOT/build-x86-v2:$LD_LIBRARY_PATH"
source "$NN_STUDY_SCRIPTS/athena_preload.sh"
nn_out="$NN_STUDY_ROOT/vectorization/validation"
mkdir -p "$nn_out"
cp "$NN_STUDY_ROOT/validation-real-athena/original.bin" "$nn_out/original.bin"
for nn_backend in direct direct_avx2 sofie_gemv; do
 "$NN_STUDY_ROOT/build-x86-v2/bench" dump "$nn_backend" "$NN_STUDY_ROOT/captured-inputs.bin" "$nn_out/$nn_backend.bin" 100000
done
env -u PYTHONHOME -u PYTHONPATH -u LD_PRELOAD /tmp/nn-model-inspection/bin/python "$NN_STUDY_SCRIPTS/validate.py" "$nn_out"
