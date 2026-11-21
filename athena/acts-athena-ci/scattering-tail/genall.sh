#!/bin/bash
# Generate the single-particle samples (ITk-only G4, no pile-up): gen/<name>/<job>/RDO.pool.root, then reco variants via gunreco.sh
# usage: genall.sh   env: NJOB (default 20), NEV (default 500), JOBS (default 12)
export SIMDET="Bpipe ITkPixel ITkStrip" NT=2
S=~/scripts/athena/acts-athena-ci/scattering-tail
for spec in "mu1 13 1" "pi1 211 1" "mu3 13 3" "pi3 211 3"; do for j in $(seq 0 $(( ${NJOB:-20} - 1 ))); do echo "$spec $j ${NEV:-500}"; done; done |
  xargs -P ${JOBS:-12} -L1 bash $S/gen.sh
echo GENALL_DONE
