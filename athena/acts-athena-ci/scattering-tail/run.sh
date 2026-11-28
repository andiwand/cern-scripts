#!/bin/bash
# One MT reco job per variant in run/scattering-tail/<tag>/<variant> (common/run.sh).
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (default 2), MODE (mt|serial)
# variants (Xi2maxSigma/Xi2maxNoAddSigma of the primary pass are 7/10, of LRT 5/7.07):
#   t0   main (tail off)                     t1   tail in the primary pass
#   tl   tail in the primary and LRT pass    c5   tail off, primary cuts 5/7
#   t5   tail in the primary pass, cuts 5/7  w10  tail off, primary cuts 10/14 (wider-cut reference)
#   c4/t4    cuts 4/6 without/with tail      c35/t35  cuts 3.5/4.6 (= chi2 15/25 in 2D, the PR's ODD cuts) without/with tail
#   g5/g4/g35  t5/t4/t35 with the tail model refitted to Geant4 (scatteringTailModel=Geant4)
#   tg1  t1 with scatteringTailGate 1 (tail only where it at least doubles the predicted variance)
#   diagnostic (ACTS_TAIL_DIAG, needs the diag build): d1 = t1 without the C + wD update,
#   d2 = t1 without re-selection on holes (outliers only), d3 = both
STUDY=scattering-tail
P=flags.Tracking.ITkActsPass
T="flags.Acts.scatteringTail=True;"
C5="$P.Xi2maxSigma=[5.];$P.Xi2maxNoAddSigma=[7.];"
C4="$P.Xi2maxSigma=[4.];$P.Xi2maxNoAddSigma=[6.];"
C35="$P.Xi2maxSigma=[3.5];$P.Xi2maxNoAddSigma=[4.6];"
G4="cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailModel='Geant4';"
variant() { JOBENV=ACTS_TAIL_DIAG=0; case $1 in
  t0) PRE="pass";;
  t1) PRE="$T";;
  tl) PRE="${T}flags.Acts.scatteringTailSecondary=True;";;
  c5) PRE="$C5";;
  t5) PRE="$T$C5";;
  g5) PRE="$T$C5"; POST="$G4";;
  c4) PRE="$C4";;
  t4) PRE="$T$C4";;
  g4) PRE="$T$C4"; POST="$G4";;
  c35) PRE="$C35";;
  t35) PRE="$T$C35";;
  g35) PRE="$T$C35"; POST="$G4";;
  w10) PRE="$P.Xi2maxSigma=[10.];$P.Xi2maxNoAddSigma=[14.];";;
  tg1) PRE="$T"; POST="cfg.getEventAlgo('ActsTrackFindingAlg').scatteringTailGate=1.0;";;
  d1|d2|d3) PRE="$T"; JOBENV=ACTS_TAIL_DIAG=${1#d};;
  *) return 1;; esac; }
source ~/scripts/athena/acts-athena-ci/common/run.sh "$@"
