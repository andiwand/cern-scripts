#!/bin/bash
# usage: stcycle.sh <tag> <first cycle> <last cycle> <script> [script ...]
# Alternating single-threaded runs of the given job scripts (e.g. st_core st_trk,
# stgap0_core stgap0_trk, stpix_on stpix_off) into run/<tag>_<script>_<i>.
# Replaces the numbered perfloop*.sh drivers of the space point work.
source /home/astefl/source/acts/acts-athena-ci/runenv.sh >/dev/null 2>&1
S=/home/astefl/scripts/athena/acts-athena-ci/strip-space-points
R=/home/astefl/source/acts/acts-athena-ci/run
TAG=$1; FIRST=$2; LAST=$3; shift 3
cd $R
for i in $(seq $FIRST $LAST); do
  for job in "$@"; do
    d=${TAG}_${job}_$i; rm -rf $d; mkdir -p $d; cd $d
    nice -n 5 bash $S/$job.sh > /dev/null 2>&1
    echo "done $d $(date +%T) load=$(cut -d' ' -f1 /proc/loadavg)"
    cd ..
  done
done
echo "STCYCLE_${TAG}_DONE"
