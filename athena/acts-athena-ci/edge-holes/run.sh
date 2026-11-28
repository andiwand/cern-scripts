#!/bin/bash
# One MT reco job per variant in run/edge-holes/<tag>/<variant> (common/run.sh).
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (default 2), MODE (mt|serial)
# variants: e0 (border 0 = old default), e001 (1 um: the check runs, nearly no physics change), e05, e1 (new default), e2,
#           p1 (= default after the primary-only config: 1 mm primary, 0 in LRT; e1 meant 1 mm in all passes before it),
#           h2 (border 0, maxHoles 2 in the primary and LRT pass, LRT pixel/strip hole caps 1 -> 2)
STUDY=edge-holes
variant() { case $1 in
  e0) PRE="flags.Acts.edgeHoleBorderWidth=0.0;";;
  e05) PRE="flags.Acts.edgeHoleBorderWidth=0.5;";;
  e001) PRE="flags.Acts.edgeHoleBorderWidth=0.001;";;
  e1|p1) PRE="pass";;
  e2) PRE="flags.Acts.edgeHoleBorderWidth=2.0;";;
  h2) PRE="flags.Acts.edgeHoleBorderWidth=0.0;flags.Tracking.ITkActsPass.maxHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxPixelHoles=[2];flags.Tracking.ITkActsLargeRadiusPass.maxSctHoles=[2];";;
  *) return 1;; esac; }
source ~/scripts/athena/acts-athena-ci/common/run.sh "$@"
