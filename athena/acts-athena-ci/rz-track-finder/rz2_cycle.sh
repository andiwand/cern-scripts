#!/bin/bash
# usage: rz2_cycle.sh <tag> <n cycles> [nevents]
# Alternating old / newgrid / new x CKF/RZ, ttbar, sequential, nothing rebuilt.
# Directories are <tag>old_<v>_<i> and <tag>new_<v>_<i>, so rzsum.py <tag>old
# and rzsum.py <tag>new summarise each build (and <tag>newgrid).
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=${1:-c}
NCYC=${2:-3}
NEV=${3:-20}
cd $R
for i in $(seq 1 $NCYC); do
  for side in old newgrid new; do
    for v in ckf rz; do
      d=${TAG}${side}_${v}_$i
      echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
      nice -n 5 bash /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rz2_job.sh $side $v ttbar $NEV $R/$d > /dev/null 2>&1
      grep -E "PerfMonMTSvc +INFO Execute" $d/log.RAWtoALL 2>/dev/null \
        | grep -E "ActsTrackFinding(Rz)?Alg *$|ActsPixelClusterizationAlg *$" | sed 's/  */ /g'
      echo "--- $d done $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    done
  done
done
echo "RZ2CYCLE_${TAG}_DONE"
