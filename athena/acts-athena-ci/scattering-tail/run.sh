#!/bin/bash
# One MT reco job per variant in run/scattering-tail/<tag>/<variant>, full-PU-truth ttbar mu=200 sample (run/edge-holes/input).
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (default 2), MODE (mt|serial)
# variants (Xi2maxSigma/Xi2maxNoAddSigma of the primary pass are 7/10, of LRT 5/7.07):
#   t0   main (tail off)                     t1   tail in the primary pass
#   tl   tail in the primary and LRT pass    c5   tail off, primary cuts 5/7
#   t5   tail in the primary pass, cuts 5/7  w10  tail off, primary cuts 10/14 (wider-cut reference)
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NT=$2; NEV=$3; shift 3
R=$A/run/scattering-tail/$TAG; mkdir -p $R
export INPUT_RDO=${INPUT_RDO:-$(ls $A/run/edge-holes/input/RDO.* | paste -sd,)}
P=flags.Tracking.ITkActsPass
pre() { case $1 in
  t0) echo "pass";;
  t1) echo "flags.Acts.scatteringTail=True;";;
  tl) echo "flags.Acts.scatteringTail=True;flags.Acts.scatteringTailSecondary=True;";;
  c5) echo "$P.Xi2maxSigma=[5.];$P.Xi2maxNoAddSigma=[7.];";;
  t5) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[5.];$P.Xi2maxNoAddSigma=[7.];";;
  w10) echo "$P.Xi2maxSigma=[10.];$P.Xi2maxNoAddSigma=[14.];";;
  *) return 1;; esac; }
run() {
  local v=$1 p; p=$(pre $v) || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/scattering-tail/runenv.sh >/dev/null 2>&1 && \
    EXTRA_PRE="$p" EXTRA_POST="" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-2})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
