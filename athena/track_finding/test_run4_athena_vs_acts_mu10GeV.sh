#!/bin/bash
# art-description: Run 4 configuration, ITK only recontruction, Single muon 10GeV, acts activated
# art-type: grid
# art-include: main/Athena
# art-output: *.root
# art-output: *.xml
# art-output: dcube*
# art-html: dcube_ambi_last

mkdir run4_athena_vs_acts_mu10GeV
cd run4_athena_vs_acts_mu10GeV

lastref_dir=last_results
dcubeXml=dcube_IDPVMPlots_ACTS_CKF_ITk_techeff.xml
rdo_23p0=/cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.900495.PG_single_muonpm_Pt10_etaFlatnp0_43.recon.RDO.e8481_s4149_r14697/RDO.33675641._000037.pool.root.1
nEvents=1000

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

# Run athena
run "Reconstruction-athena" \
    Reco_tf.py --CA \
    --steering doRAWtoALL \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude" \
    --preExec "ConfigFlags.Tracking.doStoreSiSPSeededTracks=True;ConfigFlags.Tracking.writeExtendedSi_PRDInfo=True" \
    --inputRDOFile ${rdo_23p0} \
    --outputAODFile AOD.athena.root \
    --maxEvents ${nEvents}

reco_rc=$?

# Rename log
mv log.RAWtoALL log.RAWtoALL.ATHENA

if [ $reco_rc != 0 ]; then
    exit $reco_rc
fi

run "IDPVM" \
    runIDPVM.py \
    --filesInput AOD.athena.root \
    --outputFile idpvm.athena.root \
    --validateExtraTrackCollections 'SiSPSeededTracksTrackParticles' \
    --doTechnicalEfficiency \
    --doExpertPlots

reco_rc=$?
if [ $reco_rc != 0 ]; then
    exit $reco_rc
fi

# Run acts
run "Reconstruction-acts" \
    Reco_tf.py --CA \
    --steering doRAWtoALL \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsValidateTracksFlags" \
    --preExec "flags.Tracking.doStoreSiSPSeededTracks=True;flags.Tracking.doTruth=True;flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True;flags.Tracking.writeExtendedSi_PRDInfo=True" \
    --inputRDOFile ${rdo_23p0} \
    --outputAODFile AOD.acts.root \
    --maxEvents ${nEvents}

reco_rc=$?

# Rename log
mv log.RAWtoALL log.RAWtoALL.ACTS

if [ $reco_rc != 0 ]; then
    exit $reco_rc
fi

run "IDPVM" \
    runIDPVM.py \
    --filesInput AOD.acts.root \
    --outputFile idpvm.acts.root \
    --validateExtraTrackCollections 'SiSPSeededTracksActsValidateTracksTrackParticles' \
    --doTechnicalEfficiency \
    --doExpertPlots

reco_rc=$?
if [ $reco_rc != 0 ]; then
    exit $reco_rc
fi

#echo "download latest result..."
#art.py download --user=artprod --dst="$lastref_dir" "$ArtPackage" "$ArtJobName"
#ls -la "$lastref_dir"
#
#run "dcube-ckf-last" \
#    $ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py \
#    -p -x dcube_ckf_last \
#    -c ${dcubeXmlAbsPath} \
#    -r ${lastref_dir}/idpvm.ckf.root \
#    idpvm.ckf.root
#
#run "dcube-ambi-last" \
#    $ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py \
#    -p -x dcube_ambi_last \
#    -c ${dcubeXmlAbsPath} \
#    -r ${lastref_dir}/idpvm.ambi.root \
#    idpvm.ambi.root

# Compare performance athena vs acts
run "dcube-athena-acts" \
    $ATLAS_LOCAL_ROOT/dcube/current/DCubeClient/python/dcube.py \
    -p -x dcube_athena_acts \
    -c ${dcubeXmlAbsPath} \
    -r idpvm.athena.root \
    idpvm.acts.root

runTRKAnalysis.py -i AOD.athena.root -o trk_athena.root
runTRKAnalysis.py -i AOD.acts.root -o trk_acts.root
