Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.main.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --maxEvents 100 \
    --perfmon fullmonmt \
    --multithreaded False

runIDPVM.py \
    --filesInput AOD.acts.main.root \
    --outputFile idpvm.acts.main.root \
    --OnlyTrackingPreInclude \
    --doHitLevelPlots \
    --HSFlag All \
    --doExpertPlots \
    --validateExtraTrackCollections "SiSPSeedSegmentsActsPixelTrackParticles" \
    --doTechnicalEfficiency

Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.module.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Common.MsgSuppression=False; \
    flags.Tracking.doStoreSiSPSeededTracks=True; \
    flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.ITkActsValidateTracksPass.storeSiSPSeededTracks=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True; \
    from ActsConfig.ActsConfigFlags import SeedingStrategy;flags.Acts.SeedingStrategy=SeedingStrategy.ModuleTriplet;' \
    --maxEvents 100 \
    --perfmon fullmonmt \
    --multithreaded False

runIDPVM.py \
    --filesInput AOD.acts.module.root \
    --outputFile idpvm.acts.module.root \
    --OnlyTrackingPreInclude \
    --doHitLevelPlots \
    --HSFlag All \
    --doExpertPlots \
    --validateExtraTrackCollections "SiSPSeedSegmentsActsPixelTrackParticles" \
    --doTechnicalEfficiency
