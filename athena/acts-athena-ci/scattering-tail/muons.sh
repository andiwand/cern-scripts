#!/bin/bash
# Single-muon full sim (no pile-up): reco variants per sample into run/scattering-tail/mu<pt>/<variant>.
# usage: muons.sh <nevents> <sample>... (sample = 1|10|100)   env: VARIANTS, JOBS (default 3), NT (default 8)
# 1 and 10 GeV: ATLAS-P2-RUN4-04-00-00 ART samples; 100 GeV: RUN4-03-00-01 (geometry of the ttbar sample).
export S=~/scripts/athena/acts-athena-ci/scattering-tail NEV=$1 NT=${NT:-8}; shift
D=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO
rdo() { case $1 in
  1) ls $D/ATLAS-P2-RUN4-04-00-00/*muonpm_Pt1_*/RDO.*;;
  10) ls $D/ATLAS-P2-RUN4-04-00-00/*muonpm_Pt10_*/RDO.*;;
  100) ls $D/ATLAS-P2-RUN4-03-00-01/*muonpm_Pt100_*/RDO.* | head -1;; esac; }
job() { s=$1 v=$2; case $v in g*) r=run4.sh;; *) r=run2.sh;; esac
  INPUT_RDO=$3 PAR=1 bash $S/$r mu$s $NT $NEV $v | grep RECO | sed "s/^/mu$s /"; }
export -f job
for s in "$@"; do for v in ${VARIANTS:-t0 c35 t35 g35 c5 t5 g5 w10}; do echo "$s $v $(rdo $s)"; done; done |
  xargs -P ${JOBS:-3} -L1 bash -c "job \$0 \$1 \$2"
echo MUONS_DONE
