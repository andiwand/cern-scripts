#!/bin/bash
# One MT reco job per variant in run/scattering-tail/<tag>/<variant>, full-PU-truth ttbar mu=200 sample (run/edge-holes/input).
# g5/g4/g35 = t5/t4/t35 with the tail model refitted to Geant4 (scatteringTailModel=Geant4).
# diagnostic variants (ACTS_TAIL_DIAG, needs the diag build): d1 = t1 without the C + wD update,
# d2 = t1 without re-selection on holes (outliers only), d3 = both
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (default 2), MODE (mt|serial)
# variants (Xi2maxSigma/Xi2maxNoAddSigma of the primary pass are 7/10, of LRT 5/7.07):
#   t0   main (tail off)                     t1   tail in the primary pass
#   tl   tail in the primary and LRT pass    c5   tail off, primary cuts 5/7
#   t5   tail in the primary pass, cuts 5/7  w10  tail off, primary cuts 10/14 (wider-cut reference)
#   c4/t4    cuts 4/6 without/with tail      c35/t35  cuts 3.5/4.6 (= chi2 15/25 in 2D, the PR's ODD cuts) without/with tail
#   tg1  t1 with scatteringTailGate 1 (tail only where it at least doubles the predicted variance)
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
  g5) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[5.];$P.Xi2maxNoAddSigma=[7.];";;
  g4) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[4.];$P.Xi2maxNoAddSigma=[6.];";;
  g35) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[3.5];$P.Xi2maxNoAddSigma=[4.6];";;
  tg1|d1|d2|d3) echo "flags.Acts.scatteringTail=True;";;
  c4) echo "$P.Xi2maxSigma=[4.];$P.Xi2maxNoAddSigma=[6.];";;
  t4) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[4.];$P.Xi2maxNoAddSigma=[6.];";;
  c35) echo "$P.Xi2maxSigma=[3.5];$P.Xi2maxNoAddSigma=[4.6];";;
  t35) echo "flags.Acts.scatteringTail=True;$P.Xi2maxSigma=[3.5];$P.Xi2maxNoAddSigma=[4.6];";;
  w10) echo "$P.Xi2maxSigma=[10.];$P.Xi2maxNoAddSigma=[14.];";;
  *) return 1;; esac; }
post() { case $1 in
  g5|g4|g35) echo "cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailModel='Geant4';";;
  tg1) echo "cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailGate=1.0;";;
  *) echo "";; esac; }
run() {
  local v=$1 p; p=$(pre $v) || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/scattering-tail/runenv.sh >/dev/null 2>&1 && \
    ACTS_TAIL_DIAG=$(case $v in d1) echo 1;; d2) echo 2;; d3) echo 3;; *) echo 0;; esac) EXTRA_PRE="$p" EXTRA_POST="$(post $v)" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-2})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
