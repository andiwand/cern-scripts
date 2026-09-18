#!/bin/bash
# usage: rzmu_digi.sh [pt10|pt100] [nevents]
# Single muon HITS -> RDO, no pileup, same conditions as the ttbar runs.
source /home/astefl/scripts/athena/acts-athena-ci/rz-track-finder/rzrunenv.sh >/dev/null 2>&1
R=/home/astefl/source/acts/acts-athena-ci/run
PT=${1:-pt10}
NEV=${2:-200}
case $PT in
  pt10)  DS=mc21_14TeV.900495.PG_single_muonpm_Pt10_etaFlatnp0_43.simul.HITS.e8481_s4676 ;;
  pt100) DS=mc21_14TeV.900498.PG_single_muonpm_Pt100_etaFlatnp0_43.simul.HITS.e8481_s4676 ;;
  *) echo "unknown pt $PT"; exit 1 ;;
esac
HITS=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/HITS/ATLAS-P2-RUN4-05-00-00/$DS
conditions=$(python -c "from AthenaConfiguration.TestDefaults import defaultConditionsTags; print(defaultConditionsTags.RUN4_MC)")
d=$R/mu_$PT; rm -rf $d; mkdir -p $d; cd $d
export ATHENA_CORE_NUMBER=8
Reco_tf.py \
  --inputHITSFile $(ls $HITS/* | head -4 | tr '\n' ',' | sed 's/,$//') \
  --outputRDOFile RDO.pool.root \
  --maxEvents ${NEV} \
  --conditionsTag "all:${conditions}" \
  --preInclude "Campaigns.MC23PhaseIINoPileUp,InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude" \
  --postInclude "PyJobTransforms.UseFrontier" \
  --steering "doRAWtoALL" \
  --multithreaded > digi.log 2>&1
echo "DIGI RC=$? $(ls -la RDO.pool.root 2>/dev/null | awk '{print $5}')"
