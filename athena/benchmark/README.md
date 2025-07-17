ACTS

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.acts.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude,ActsConfig.ActsCIFlags.actsWorkflowFlags" \
    --preExec 'flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.ITkActsPass.storeTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --maxEvents 10 \
    --perfmon fullmonmt \
    --multithreaded False
```

Legacy

```
Reco_tf.py \
    --inputRDOFile /cvmfs/atlas-nightlies.cern.ch/repo/data/data-art/PhaseIIUpgrade/RDO/ATLAS-P2-RUN4-03-00-00/mc21_14TeV.601229.PhPy8EG_A14_ttbar_hdamp258p75_SingleLep.recon.RDO.e8481_s4149_r14700/RDO.33629020._000047.pool.root.1 \
    --outputAODFile AOD.legacy.root \
    --preInclude "InDetConfig.ConfigurationHelpers.OnlyTrackingPreInclude" \
    --preExec 'flags.Tracking.doTruth=True; \
    flags.Tracking.doITkFastTracking=True; \
    flags.Tracking.writeExtendedSi_PRDInfo=True; \
    flags.Tracking.doStoreTrackSeeds=True; \
    flags.Tracking.doPixelDigitalClustering=True;' \
    --maxEvents 10 \
    --perfmon fullmonmt \
    --multithreaded False
```
