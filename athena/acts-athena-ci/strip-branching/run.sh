#!/bin/bash
# One MT reco job per variant in run/strip-branching/<tag>/<variant> (common/run.sh).
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO, PAR (default 2), MODE (mt|serial)
# variants (primary pass ActsTrackFindingAlg only, 2 measurements kept per surface in the regions):
#   b0    main
#   bP1   strip barrel layer 0, pixel seeds        bP2   strip barrel layers 0-1, pixel seeds
#   bA2   strip barrel layers 0-1, all seeds       bP2e  bP2 + EdgeHoleBorderWidth 1 mm (= MR 92667)
#   e1    EdgeHoleBorderWidth 1 mm only
#   sP    all strip layers (barrel + endcap), pixel seeds   eP0  strip endcap disk 0, pixel seeds
#   bPe0  strip barrel layer 0 + endcap disk 0, pixel seeds
STUDY=strip-branching
F="cfg.getEventAlgo('ActsTrackFindingAlg')"
L1="$F.measurementSelectorRegions=['strip:barrel:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2];"
L2="$F.measurementSelectorRegions=['strip:barrel:0','strip:barrel:1'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
PIX="$F.measurementSelectorRegionSeedLabels=['PPP'];"
E="$F.EdgeHoleBorderWidth=1.0;"
SA="$F.measurementSelectorRegions=['strip:barrel:*','strip:endcap:*'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
SE0="$F.measurementSelectorRegions=['strip:endcap:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2];"
SBE0="$F.measurementSelectorRegions=['strip:barrel:0','strip:endcap:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
variant() { case $1 in
  b0) POST="";;
  bP1) POST="$L1$PIX";;
  bP2) POST="$L2$PIX";;
  bA2) POST="$L2";;
  bP2e) POST="$L2$PIX$E";;
  e1) POST="$E";;
  sP) POST="$SA$PIX";;
  eP0) POST="$SE0$PIX";;
  bPe0) POST="$SBE0$PIX";;
  *) return 1;; esac; }
source ~/scripts/athena/acts-athena-ci/common/run.sh "$@"
