#!/bin/bash
# Primary-pass ITk reconstruction of existing RDOs, AOD export (rows.tsv), logs and exit-code marker.
# usage: run.sh OUT VARIANT EVENTS SKIP [THREADS=8] [SCORING=1]
# VARIANT  core4 core5 core7 core10 core14 tail4 tail5 tail7: measurement/outlier gates 4/6 5/7 7/10 10/14 14/20;
#          (core|tail)<meas>u<outlier>h<maxHoles>o<maxOutliers>, e.g. core10u14h1o2, also sets maxHoles/maxOutliers.
#          tail* enables the Geant4 scattering-tail mixture; bremsstrahlung recovery is always off.
# SCORING  1 records the predictive mixture score on tracks (does not change reconstruction).
# env: LIB=default|onnx|native  private libActsTrackReconstruction from build_nn.py / build_nn_native.py
#      NN=0|1                   install the all-charge pixel NN calibrator (nn_config.py; NN_MODE=pre|post)
#      INPUT=rdo1,rdo2,...      input RDOs (default: the edge-holes ttbar mu200 RDOs)
set -o pipefail
SCORE_SCRIPTS=$(cd "$(dirname "$0")" && pwd)
SCORE_OUT=$1; SCORE_VARIANT=$2; SCORE_EVENTS=$3; SCORE_SKIP=$4
SCORE_THREADS=${5:-8}; SCORE_RECORD=${6:-1}
SCORE_BASE=/home/astefl/source/acts/acts-athena-ci
case "${LIB:=default}" in
  default) SCORE_LIB=;;
  onnx) SCORE_LIB=$SCORE_BASE/run/scattering-tail-score/nn-control/lib;;
  native) SCORE_LIB=$SCORE_BASE/run/scattering-tail-score/nn-native-control/lib;;
  *) echo "Unknown LIB=$LIB"; exit 2;;
esac
mkdir "$SCORE_OUT" || exit 1
cd "$SCORE_OUT" || exit 1
source /home/astefl/scripts/athena/acts-athena-ci/scattering-tail/env.sh
source "$SCORE_BASE/athena-build-tail-score/x86_64-el9-gcc15-opt/setup.sh"
[[ -n "$SCORE_LIB" ]] && export LD_LIBRARY_PATH="$SCORE_LIB:$LD_LIBRARY_PATH"
set -e
trap 'echo $? > exit-code' EXIT
SCORE_HOLES=; SCORE_OUTLIERS=
case "$SCORE_VARIANT" in
  core4|tail4) SCORE_CUT=4.; SCORE_OUTLIER=6.;;
  core5|tail5) SCORE_CUT=5.; SCORE_OUTLIER=7.;;
  core7|tail7) SCORE_CUT=7.; SCORE_OUTLIER=10.;;
  core10) SCORE_CUT=10.; SCORE_OUTLIER=14.;;
  core14) SCORE_CUT=14.; SCORE_OUTLIER=20.;;
  *)
    if [[ "$SCORE_VARIANT" =~ ^(core|tail)([0-9]+)u([0-9]+)h([0-2])o([0-2])$ ]]; then
      SCORE_CUT=${BASH_REMATCH[2]}; SCORE_OUTLIER=${BASH_REMATCH[3]}
      SCORE_HOLES=${BASH_REMATCH[4]}; SCORE_OUTLIERS=${BASH_REMATCH[5]}
      (( SCORE_OUTLIER >= SCORE_CUT )) || exit 2
    else
      echo "Unknown variant"; exit 2
    fi;;
esac
SCORE_TAIL=False; [[ "$SCORE_VARIANT" = tail* ]] && SCORE_TAIL=True
SCORE_ENABLED=False; [[ "$SCORE_RECORD" = 1 ]] && SCORE_ENABLED=True
SCORE_INPUT=${INPUT:-$(python -c 'import glob;print(",".join(sorted(glob.glob("/home/astefl/source/acts/acts-athena-ci/run/edge-holes/input/RDO.*"))))')}
SCORE_CONDITIONS=$(python -c 'from AthenaConfiguration.TestDefaults import defaultConditionsTags;print(defaultConditionsTags.RUN4_MC)')
SCORE_PRE="flags.Acts.scatteringTail=$SCORE_TAIL;flags.Acts.scatteringTailSecondary=False;flags.Acts.doBremRecovery=False;flags.Tracking.ITkActsPass.Xi2maxSigma=[$SCORE_CUT];flags.Tracking.ITkActsPass.Xi2maxNoAddSigma=[$SCORE_OUTLIER];"
[[ -n "$SCORE_HOLES" ]] && SCORE_PRE+="flags.Tracking.ITkActsPass.maxHoles=[$SCORE_HOLES];flags.Tracking.ITkActsPass.maxOutliers=[$SCORE_OUTLIERS];"
SCORE_POST="cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailScoring=$SCORE_ENABLED;cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailModel='Geant4';"
if [[ "${NN:-0}" = 1 ]]; then
  SCORE_POST+="exec(open('$SCORE_SCRIPTS/nn_config.py').read());"
  cp "$SCORE_SCRIPTS/nn_config.py" nn_config.py
fi
[[ -n "$SCORE_LIB" ]] && sha256sum "$SCORE_LIB/libActsTrackReconstruction.so" > library-sha256.txt
printf '%s\n' "$SCORE_PRE" "$SCORE_POST" > settings.txt
export ACTS_TAIL_DIAG=0 ATHENA_CORE_NUMBER=$SCORE_THREADS NN_BACKEND=$LIB
Reco_tf.py --maxEvents "$SCORE_EVENTS" --skipEvents "$SCORE_SKIP" \
  --perfmon fullmonmt --multithreaded True \
  --conditionsTag "all:$SCORE_CONDITIONS" --postInclude all:PyJobTransforms.UseFrontier \
  --preInclude InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude \
  --preExec "all:$SCORE_PRE" --postExec "all:$SCORE_POST" \
  --inputRDOFile "$SCORE_INPUT" --outputAODFile myAOD.pool.root --jobNumber 1 > reco.log 2>&1
python "$SCORE_SCRIPTS/extract.py" myAOD.pool.root rows.tsv "$SCORE_EVENTS" > extract.log 2>&1
