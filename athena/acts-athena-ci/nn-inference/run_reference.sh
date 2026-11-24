#!/usr/bin/env bash
# Matched raw/post reference: NN_REFERENCE_CALIBRATION=raw|post.
# OUTDIR BACKEND EVENTS INPUT_RDO [THREADS=0, zero means serial]
set -eo pipefail
nn_out=$(realpath -m "$1"); nn_backend=$2; nn_events=$3; nn_input=$4; nn_threads=${5:-0}
mkdir -p "$nn_out"
cd "$nn_out"
if [[ -e reco.log ]]; then echo "Refusing to overwrite $nn_out" >&2; exit 2; fi
set +e
source /home/astefl/scripts/athena/acts-athena-ci/nn-inference/env.sh > environment.log 2>&1
set -e
source /home/astefl/source/acts/acts-athena-ci/athena-build-nn-inference/x86_64-el9-gcc15-opt/setup.sh >> environment.log 2>&1
nn_library_dir="$NN_STUDY_ROOT/build"
if [[ "$nn_backend" == direct_blocked ]]; then nn_library_dir="$NN_STUDY_ROOT/build-blocked"; fi
export LD_LIBRARY_PATH="$nn_library_dir:$LD_LIBRARY_PATH"
export NN_STUDY_BACKEND=$nn_backend
export SEED_POLICY_VARIANT=SeedOnly SEED_POLICY_CALIBRATION=${NN_REFERENCE_CALIBRATION:-post}
export ATHENA_CORE_NUMBER=${nn_threads:-1} TRF_ECHO=1
nn_mt=False
if ((nn_threads>0)); then nn_mt=True; else export ATHENA_CORE_NUMBER=1; fi
nn_pre='flags.Reco.EnableHGTDExtension=False;from ActsConfig.ActsConfigFlags import SeedMeasurementPolicy;flags.Acts.SeedMeasurementPolicy=SeedMeasurementPolicy.SeedOnly;'
nn_post="exec(open('/home/astefl/scripts/athena/acts-athena-ci/nn-inference/fixtures/config.py').read())"
sha256sum /home/astefl/source/acts/acts-athena-ci/athena-build-nn-inference/x86_64-el9-gcc15-opt/lib/libActsTrackReconstruction.so "$nn_library_dir/libNNInferenceStudy.so" > libraries.txt
printf '%s\n' "$nn_input" > input.txt
printf '%s\n' "$nn_backend" > backend.txt
printf '%s\n' "$SEED_POLICY_CALIBRATION" > calibration.txt
date -u +%FT%TZ > start.txt
uptime > load-start.txt
set +e
Reco_tf.py --maxEvents "$nn_events" --perfmon fullmonmt --multithreaded "$nn_mt" \
 --conditionsTag all:COND-MC21-SDR-RUN4-06 --postInclude all:PyJobTransforms.UseFrontier \
 --preInclude InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude \
 --preExec "all:$nn_pre" --postExec "all:$nn_post" \
 --inputRDOFile "$nn_input" --outputAODFile myAOD.pool.root --jobNumber 1 > reco.log 2>&1
nn_rc=$?
printf '%s\n' "$nn_rc" > exit-code.txt
date -u +%FT%TZ > finish.txt
uptime > load-end.txt
echo "$nn_out: RC=$nn_rc"
exit "$nn_rc"
