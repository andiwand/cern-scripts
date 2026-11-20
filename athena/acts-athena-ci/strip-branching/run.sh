#!/bin/bash
# One MT reco job per variant in run/strip-branching/<tag>/<variant>, full-PU-truth ttbar mu=200 sample.
# usage: run.sh <tag> <nthreads> <nevents> <variant>...   env: INPUT_RDO (default: run/edge-holes/input), PAR (default 2), MODE (mt|serial)
# variants (primary pass ActsTrackFindingAlg only, 2 measurements kept per surface in the regions):
#   b0    main
#   bP1   strip barrel layer 0, pixel seeds        bP2   strip barrel layers 0-1, pixel seeds
#   bA2   strip barrel layers 0-1, all seeds       bP2e  bP2 + EdgeHoleBorderWidth 1 mm (= MR 92667)
#   e1    EdgeHoleBorderWidth 1 mm only
#   sP    all strip layers (barrel + endcap), pixel seeds   eP0  strip endcap disk 0, pixel seeds
#   bPe0  strip barrel layer 0 + endcap disk 0, pixel seeds
A=/home/astefl/source/acts/acts-athena-ci
TAG=$1; NT=$2; NEV=$3; shift 3
R=$A/run/strip-branching/$TAG; mkdir -p $R
export INPUT_RDO=${INPUT_RDO:-$(ls $A/run/edge-holes/input/RDO.* | paste -sd,)}
F="cfg.getEventAlgo('ActsTrackFindingAlg')"
L1="$F.measurementSelectorRegions=['strip:barrel:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2];"
L2="$F.measurementSelectorRegions=['strip:barrel:0','strip:barrel:1'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
PIX="$F.measurementSelectorRegionSeedLabels=['PPP'];"
E="$F.EdgeHoleBorderWidth=1.0;"
SA="$F.measurementSelectorRegions=['strip:barrel:*','strip:endcap:*'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
SE0="$F.measurementSelectorRegions=['strip:endcap:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2];"
SBE0="$F.measurementSelectorRegions=['strip:barrel:0','strip:endcap:0'];$F.measurementSelectorRegionNumMeasurementsCutOff=[2,2];"
post() { case $1 in
  b0) echo "";;
  bP1) echo "$L1$PIX";;
  bP2) echo "$L2$PIX";;
  bA2) echo "$L2";;
  bP2e) echo "$L2$PIX$E";;
  e1) echo "$E";;
  sP) echo "$SA$PIX";;
  eP0) echo "$SE0$PIX";;
  bPe0) echo "$SBE0$PIX";;
  *) return 1;; esac; }
run() {
  local v=$1 p; p=$(post $v) || { echo "bad variant $v"; return; }
  d=$R/$v; rm -rf $d; mkdir -p $d
  ( cd $d && source ~/scripts/athena/acts-athena-ci/strip-branching/env.sh && \
    source $A/athena-build-branching/x86_64-el9-gcc15-opt/setup.sh >/dev/null 2>&1 && \
    EXTRA_PRE="" EXTRA_POST="$p" bash ~/scripts/athena/acts-athena-ci/mr92381/spotjob.sh $NT $NEV ${MODE:-mt} | sed "s/^/$v /" )
}
i=0
for v in "$@"; do run $v & i=$((i+1)); [ $((i % ${PAR:-2})) -eq 0 ] && wait; done
wait; echo RUN_DONE_$TAG
