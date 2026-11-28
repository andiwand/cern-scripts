#!/bin/bash
# run_nn.sh output-directory variant events skip [threads=8] [scoring=1]; NN_MODE=pre|post
set -o pipefail
SCORE_SCRIPTS=$(cd "$(dirname "$0")" && pwd)
SCORE_OUT=$1; SCORE_VARIANT=$2; SCORE_EVENTS=$3; SCORE_SKIP=$4
SCORE_THREADS=${5:-8}; SCORE_RECORD=${6:-1}
SCORE_BASE=/home/astefl/source/acts/acts-athena-ci
mkdir "$SCORE_OUT" || exit 1
cd "$SCORE_OUT" || exit 1
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source "$SCORE_BASE/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh"
export LD_LIBRARY_PATH="$SCORE_BASE/run/scattering-tail-score/nn-native-control/lib:$LD_LIBRARY_PATH"
set -e
trap 'echo $? > exit-code' EXIT
case "$SCORE_VARIANT" in
  core4|tail4) SCORE_CUT=4.; SCORE_OUTLIER=6.;;
  core5|tail5) SCORE_CUT=5.; SCORE_OUTLIER=7.;;
  core7|tail7) SCORE_CUT=7.; SCORE_OUTLIER=10.;;
  core10) SCORE_CUT=10.; SCORE_OUTLIER=14.;;
  core14) SCORE_CUT=14.; SCORE_OUTLIER=20.;;
  *) echo "Unknown variant"; exit 2;;
esac
SCORE_TAIL=False; [[ "$SCORE_VARIANT" = tail* ]] && SCORE_TAIL=True
SCORE_ENABLED=False; [[ "$SCORE_RECORD" = 1 ]] && SCORE_ENABLED=True
SCORE_INPUT=$(python -c 'import glob;print(",".join(sorted(glob.glob("/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.*"))))')
SCORE_CONDITIONS=$(python -c 'from AthenaConfiguration.TestDefaults import defaultConditionsTags;print(defaultConditionsTags.RUN4_MC)')
SCORE_PRE="flags.Acts.scatteringTail=$SCORE_TAIL;flags.Acts.scatteringTailSecondary=False;flags.Acts.doBremRecovery=False;flags.Tracking.ITkActsPass.Xi2maxSigma=[$SCORE_CUT];flags.Tracking.ITkActsPass.Xi2maxNoAddSigma=[$SCORE_OUTLIER];"
SCORE_POST="cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailScoring=$SCORE_ENABLED;cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailModel='Geant4';"
SCORE_POST+="exec(open('$SCORE_SCRIPTS/nn_native_config.py').read());"
cp "$SCORE_SCRIPTS/nn_native_config.py" nn_native_config.py
sha256sum "$SCORE_BASE/run/scattering-tail-score/nn-native-control/lib/libActsTrackReconstruction.so" > library-sha256.txt
printf '%s\n' "$SCORE_PRE" "$SCORE_POST" > settings.txt
export ACTS_TAIL_DIAG=0 ATHENA_CORE_NUMBER=$SCORE_THREADS
Reco_tf.py --maxEvents "$SCORE_EVENTS" --skipEvents "$SCORE_SKIP" \
  --perfmon fullmonmt --multithreaded True \
  --conditionsTag "all:$SCORE_CONDITIONS" --postInclude all:PyJobTransforms.UseFrontier \
  --preInclude InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude \
  --preExec "all:$SCORE_PRE" --postExec "all:$SCORE_POST" \
  --inputRDOFile "$SCORE_INPUT" --outputAODFile myAOD.pool.root --jobNumber 1 > reco.log 2>&1
python "$SCORE_SCRIPTS/extract.py" myAOD.pool.root rows.tsv "$SCORE_EVENTS" > extract.log 2>&1
