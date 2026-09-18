#!/bin/bash
# usage: pixcycle.sh <tagprefix> <n cycles> [nevents]
# Alternating ActsCore / ActsTrk pixel space point formation in one build.
source /home/astefl/scripts/athena/acts-athena-ci/pixel-space-points/pixrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=${1:-p}
NCYC=${2:-3}
NEV=${3:-20}
cd $R
for i in $(seq 1 $NCYC); do
  for v in core trk; do
    d=${TAG}_${v}_$i; rm -rf $d; mkdir -p $d; cd $d
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    nice -n 5 bash /home/astefl/scripts/athena/acts-athena-ci/pixel-space-points/pix_common.sh $v $NEV > /dev/null 2>&1
    grep -E "PerfMonMTSvc +INFO Execute" log.RAWtoALL 2>/dev/null | grep -E "ActsPixelSpacePointFormationAlg|ActsPixelClusterizationAlg" | sed 's/  */ /g'
    echo "--- $d done $(date +%T)"
    cd ..
  done
done
echo "PIXCYCLE_${TAG}_DONE"
