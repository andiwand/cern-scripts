#!/bin/bash
# usage: rzbins.sh <tag> [nevents]
# The RZ finder alone with different measurement binnings; the layout is
# rebuilt per job, nothing is recompiled. Prints the finder time and its
# per-stop module and bin counts for each.
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=${1:-bins}
NEV=${2:-20}
cd $R
for cfg in "64 20" "128 20" "256 20" "128 10" "256 10" "512 10"; do
  set -- $cfg
  d=${TAG}_p$1_a$2; rm -rf $d; mkdir -p $d; cd $d
  echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
  nice -n 5 bash /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz_common.sh rz $NEV "flags.Acts.Rz.PhiBins=$1; flags.Acts.Rz.AlongBinWidth=$2.0;" > /dev/null 2>&1
  grep -E "PerfMonMTSvc +INFO Execute" log.RAWtoALL | grep -E "TrackFindingRzAlg|PixelClusterizationAlg" | sed 's/  */ /g'
  grep -h "RZ track finding:\|RZ seed loop\|RZ layout:" log.RAWtoALL | sed 's/.*INFO //'
  cd ..
done
echo "RZBINS_${TAG}_DONE"
