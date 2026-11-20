#!/bin/bash
# One MT reco job per variant in run/edge-holes/<tag>/<variant>, full-PU-truth ttbar mu=200 sample.
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO (default: all of run/edge-holes/input), PAR (parallel jobs, default 2), MODE (mt|serial)
# variants: e0 (border 0 = old default), e001 (1 um: the check runs, nearly no physics change), e05, e1 (new default), e2,
#           p1 (= default after the primary-only config: 1 mm primary, 0 in LRT; e1 meant 1 mm in all passes before it),
#           h2 (border 0, maxHoles 2 in the primary and LRT pass, LRT pixel/strip hole caps 1 -> 2)
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NT=$2; NEV=$3; shift 3
R=$A/run/edge-holes/$TAG; mkdir -p $R
export INPUT_RDO=${INPUT_RDO:-$(ls $A/run/edge-holes/input/RDO.* | paste -sd,)}
pre() { case $1 in
  e0) echo "flags.Acts.edgeHoleBorderWidth=0.0;";;
  e05) echo "flags.Acts.edgeHoleBorderWidth=0.5;";;
  e001) echo "flags.Acts.edgeHoleBorderWidth=0.001;";;
  e1) echo "pass";;
  p1) echo "pass";;
  e2) echo "flags.Acts.edgeHoleBorderWidth=2.0;";;
  h2) echo "flags.Acts.edgeHoleBorderWidth=0.0;flags.Tracking.ITkActsPass.maxHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxPixelHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxSctHoles=[2];";;
  *) return 1;; esac; }
run() {
  local v=$1 p; p=$(pre $v) || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/edge-holes/env.sh && \
    source $A/athena-build-edgehole/x86_64-el9-gcc15-opt/setup.sh >/dev/null 2>&1 && \
    EXTRA_PRE="$p" EXTRA_POST="" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-2})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
