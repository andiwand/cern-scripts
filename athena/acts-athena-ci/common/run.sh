#!/bin/bash
# Shared driver of a study's run.sh: one reco job per variant in run/<study>/<tag>/<variant>,
# full-PU-truth ttbar mu=200 sample, in the study's build (BUILD_DIR of <study>/env.sh).
# The study's run.sh sets STUDY, defines variant() and sources this file with its arguments:
#   variant <v>   sets PRE (preExec), POST (postExec), JOBENV (extra "VAR=value ..." for the job); returns 1 if unknown
# usage: <study>/run.sh <tag> <nthreads> <nevents> <variant>...
# env: INPUT_RDO (default: all of run/edge-holes/input), PAR (parallel jobs, default 2), MODE (mt|serial),
#      SPOTJOB (the job script, default ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh)
: "${STUDY:?set STUDY before sourcing common/run.sh}"
A=/home/astefl/source/acts/acts-athena-ci
SPOTJOB=${SPOTJOB:-~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh}
TAG=$1; NT=$2; NEV=$3; shift 3
R=$A/run/$STUDY/$TAG; mkdir -p $R
export INPUT_RDO=${INPUT_RDO:-$(ls $A/run/edge-holes/input/RDO.* | paste -sd,)}
run() {
  local v=$1 d PRE= POST= JOBENV=
  variant $v || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/common/runenv.sh $STUDY >/dev/null 2>&1 && \
    env $JOBENV EXTRA_PRE="$PRE" EXTRA_POST="$POST" bash $SPOTJOB $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-2})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
