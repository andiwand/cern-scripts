#!/bin/bash
# Alternating ACTS (Gbts) vs legacy (GbtsFtf) timing, same build, single threaded.
R=/home/astefl/source/acts/acts-athena-ci/run
N=${NEVENTS:-20}
for i in 1 2 3; do
  /home/astefl/scripts/athena/acts-athena-ci/gbts/timeone.sh pr Gbts    v2acts_$i $N
  /home/astefl/scripts/athena/acts-athena-ci/gbts/timeone.sh pr GbtsFtf v2ftf_$i  $N
done
echo "TIMELEGACY_DONE"
