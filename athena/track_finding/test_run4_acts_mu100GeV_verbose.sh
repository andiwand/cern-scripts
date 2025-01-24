#!/bin/bash
# art-description: Run 4 configuration, ITK only recontruction, Single muon 100GeV, acts activated
# art-type: grid
# art-include: main/Athena
# art-output: *.root
# art-output: *.xml
# art-output: dcube*
# art-html: dcube_ambi_last

mkdir run4_acts_mu100GeV_verbose
cd run4_acts_mu100GeV_verbose

lastref_dir=last_results
dcubeXml=dcube_IDPVMPlots_ACTS_CKF_ITk_techeff.xml
rdo_23p0=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.900498.PG_single_muonpm_Pt100_etaFlatnp0_43.recon.RDO.e8481_s4149_r14697/RDO.33675668._000016.pool.root.1
nEvents=1000
sEvents=0

# search in $DATAPATH for matching file
dcubeXmlAbsPath=$(find -H ${DATAPATH//:/ } -mindepth 1 -maxdepth 1 -name $dcubeXml -print -quit 2>/dev/null)
# Don't run if dcube config not found
if [ -z "$dcubeXmlAbsPath" ]; then
    echo "art-result: 1 dcube-xml-config"
    exit 1
fi

run () {
    name="${1}"
    cmd="${@:2}"
    ############
    echo "Running ${name}..."
    time ${cmd}
    rc=$?
    # Only report hard failures for comparison Acts-Trk since we know
    # they are different. We do not expect this test to succeed
    [ "${name}" = "dcube-ckf-ambi" ] && [ $rc -ne 255 ] && rc=0
    echo "art-result: $rc ${name}"
    return $rc
}

# Run acts
run "Reconstruction-acts" \
    Reco_tf.py --CA \
    --steering doRAWtoALL \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsValidateTracksFlags" \
    --preExec "flags.Common.MsgSuppression=False;flags.Tracking.doStoreSiSPSeededTracks=True;flags.Tracking.doTruth=True;flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True;flags.Tracking.writeExtendedSi_PRDInfo=True" \
    --postExec "cfg.getEventAlgo('ActsValidateTracksTrackFindingAlg').OutputLevel=1" \
    --inputRDOFile ${rdo_23p0} \
    --outputAODFile AOD.acts.root \
    --maxEvents ${nEvents} \
    --skipEvents ${sEvents} \
    --multithreaded False

reco_rc=$?

if [ $reco_rc != 0 ]; then
    exit $reco_rc
fi

runTRKAnalysis.py -i AOD.acts.root -o trk_acts.root
