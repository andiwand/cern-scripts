#!/bin/bash
# GBTS seed split variants, one MT job each in run/gbts-seed-split/<tag>/<variant>.
# Full-truth sample: INPUT_RDO=$(ls run/gbts-seed-split/input/RDO.* | paste -sd,)
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (parallel jobs, default 4), MODE (mt|serial)
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NT=$2; NEV=$3; shift 3
R=$A/run/gbts-seed-split/$TAG; mkdir -p $R
T="cfg.getEventAlgo('ActsPixelSeedingAlg').SeedTool"
S="cfg.getEventAlgo('ActsStripSeedingAlg').SeedTool"
F="cfg.getEventAlgo('ActsTrackFindingAlg')"
D="cfg.getEventAlgo('ActsTrackFindingAlg').SeedDestiny=['ActsPixelSeedsDestiny','ActsStripSeedsDestiny'];from AthenaConfiguration.ComponentFactory import CompFactory;cfg.addEventAlgo(CompFactory.ActsTrk.GbtsSplitDiagAlg());"
P() { echo "[setattr(t, k, v) for t in cfg.getEventAlgo('ActsTrackFindingAlg').TrackParamsEstimationTool if t.name == 'PixelTrackParamsEstimationTool' for k, v in $1.items()];"; }
post() {   # variant -> postExec
  case $1 in
    on|nightly) echo "";;
    off)     echo "$T.maxSeedSplitEta=0.0;";;
    offall)  echo "$T.maxSeedSplitEta=0.0;$S.maxSeedSplitEta=0.0;";;
    offstrip) echo "$S.maxSeedSplitEta=0.0;";;
    tol3)    echo "$T.maxInvRadDiff=2.1e-5;";;
    eta1)    echo "$T.maxSeedSplitEta=1.0;";;
    on-nf)   echo "";;
    off-nf)  echo "$T.maxSeedSplitEta=0.0;";;
    on-inf2)  P "{'initialVarInflation': [1., 1., 4., 4., 4., 1.]}";;
    off-inf2) echo "$T.maxSeedSplitEta=0.0;$(P "{'initialVarInflation': [1., 1., 4., 4., 4., 1.]}")";;
    on-pt3)   P "{'initialSigmaPtRel': 0.3}";;
    off-pt3)  echo "$T.maxSeedSplitEta=0.0;$(P "{'initialSigmaPtRel': 0.3}")";;
    on-fit)   P "{'parameterEstimationMode': 4, 'spacePointWeightExponent': 3.0}";;
    off-fit)  echo "$T.maxSeedSplitEta=0.0;$(P "{'parameterEstimationMode': 4, 'spacePointWeightExponent': 3.0}")";;
    on-diag)  echo "$D";;
    off-diag) echo "$T.maxSeedSplitEta=0.0;$D";;
    on-b)           echo "";;
    off-retry06)    echo "$T.maxSeedSplitEta=0.0;$F.retrySubSeedsMinSize=4;$F.retrySubSeedsMaxAbsEta=0.6;";;
    off-retry)      echo "$T.maxSeedSplitEta=0.0;$F.retrySubSeedsMinSize=4;";;
    on-retry)       echo "$F.retrySubSeedsMinSize=4;";;
    *) return 1;;
  esac
}
pre() { case $1 in *-nf) echo "flags.Acts.forceTrackOnSeed=False;";; *) echo "";; esac; }
run() {
  local v=$1 p; p=$(post $v) || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/gbts-seed-split/env.sh && \
    { [ $v = nightly ] || source $A/athena-build-gbtssplit/x86_64-el9-gcc15-opt/setup.sh >/dev/null 2>&1; } && \
    EXTRA_PRE="$(pre $v)" EXTRA_POST="$p" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-4})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
