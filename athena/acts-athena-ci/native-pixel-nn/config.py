"""Primary-pass NN only, with main's seed and measurement policies unchanged."""
import os
from ActsConfig.ActsMeasurementCalibrationConfig import ActsNNClusteringToolCfg
algo = cfg.getEventAlgo('ActsTrackFindingAlg')
algo.PixelCalibrator = cfg.popToolsAndMerge(ActsNNClusteringToolCfg(
    flags, name='NativeNNValidation',
    CalibrateAfterMeasurementSelection=os.environ.get('NATIVE_NN_STAGE', 'post') == 'post',
    minClusterChargeForNN=float(os.environ.get('NATIVE_NN_THRESHOLD', '0')),
    minClusterSizeForNN=0))
print('NATIVE_NN_VALIDATION', flags.Acts.PixelNNInferenceBackend,
      algo.forceTrackOnSeed, algo.chi2CutOffSigma, algo.chi2OutlierCutOffSigma,
      algo.minPixelHits, algo.PixelCalibrator)
