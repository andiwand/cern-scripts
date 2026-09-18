#!/bin/bash
# Sequential, alternating timing cycles for the strip-only study.
# Never run anything else at the same time: CPU numbers scatter under load.
CYCLES=${1:-2}; NEV=${2:-5}
cd /home/astefl/source/acts/acts-athena-ci
T="cfg.getEventAlgo('ActsLegacyStripSeedingAlg').SeedTool"
for c in $(seq 1 $CYCLES); do
  PERFMON=1 /home/astefl/scripts/athena/acts-athena-ci/gbts/strip_go.sh t_grid_$c grid off $NEV
  PERFMON=1 /home/astefl/scripts/athena/acts-athena-ci/gbts/strip_go.sh t_gbts_$c gbts off $NEV
  PERFMON=1 EXTRA_POST="${T}.addTriplets=True;${T}.maxEtaAddTriplets=4.5;" /home/astefl/scripts/athena/acts-athena-ci/gbts/strip_go.sh t_trip_$c gbts off $NEV
done
echo "TIMING DONE"
