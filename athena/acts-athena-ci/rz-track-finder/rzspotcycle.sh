#!/bin/bash
# usage: rzspotcycle.sh <tagprefix> <cycles> <threads> <events>
# SPOT-style (multithreaded) alternating CKF / RZ, throughput per side.
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=${1:-s}
NCYC=${2:-2}
NTHREADS=${3:-8}
NEV=${4:-100}
cd $R
for i in $(seq 1 $NCYC); do
  for v in ckf rz; do
    d=${TAG}_${v}_$i; rm -rf $d; mkdir -p $d; cd $d
    echo "--- $d start $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    bash /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzspot.sh $v $NTHREADS $NEV > /dev/null 2>&1
    grep -E 'Event Loop|Total Wall|evt/s|Snapshot' log.RAWtoALL 2>/dev/null | head -8 | sed 's/  */ /g'
    echo "--- $d done $(date +%T)"
    cd ..
  done
done
echo "RZSPOT_${TAG}_DONE"
