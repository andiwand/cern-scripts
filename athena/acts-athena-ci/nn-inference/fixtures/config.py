"""Matched primary-only seed-policy comparison; all-charge pixel NN, fixed cuts."""
import os
from ActsConfig.ActsMeasurementCalibrationConfig import ActsNNClusteringToolCfg
variant = os.environ['SEED_POLICY_VARIANT']
calibration = os.environ.get('SEED_POLICY_CALIBRATION', 'post')
a = cfg.getEventAlgo('ActsTrackFindingAlg')
if calibration != 'raw':
    a.PixelCalibrator = cfg.popToolsAndMerge(ActsNNClusteringToolCfg(
        flags, name='SeedPolicyNN', CalibrateAfterMeasurementSelection=calibration == 'post',
        minClusterChargeForNN=0., minClusterSizeForNN=0))
assert list(a.chi2CutOffSigma) == [7.]
assert list(a.chi2OutlierCutOffSigma) == [10.]
assert list(a.minPixelHits) == [3]
print('POLICY_FLAGS', variant, calibration, flags.GeoModel.AtlasVersion,
      flags.Acts.TrackingGeometry.UseBlueprint, flags.Acts.StripCalibrationStrategy)
for algo in cfg.getEventAlgos():
    if algo.getType() == 'ActsTrk::TrackFindingAlg':
        policy = algo.forceTrackOnSeed if variant.startswith('main') else algo.seedMeasurementPolicy
        print('POLICY_CKF', algo.getName(), policy, algo.PixelCalibrator,
              algo.chi2CutOffSigma, algo.chi2OutlierCutOffSigma, algo.minPixelHits)
        if algo.getName() != 'ActsTrackFindingAlg':
            assert policy in (False, 'Unrestricted'), (algo.getName(), policy)
for name in ['ActsPixelSeedingAlg', 'ActsStripSeedingAlg']:
    print('POLICY_SEED', name, cfg.getEventAlgo(name).SeedTool.minPt)
