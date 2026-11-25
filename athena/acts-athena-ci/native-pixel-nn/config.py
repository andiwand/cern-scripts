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

# Override only the study conditions for the incompatible-model fallback smoke job.
if model_folder := os.environ.get('NATIVE_NN_MODEL_DIR'):
    from pathlib import Path
    model_path = Path(model_folder)
    os.environ['CALIBPATH'] = str(model_path.parent) + ':' + os.environ.get('CALIBPATH', '')
    cfg.getCondAlgo(f'PixelClusterNN{flags.Acts.PixelNNInferenceBackend.value}CondAlg').ModelPaths = [
        f'{model_path.name}/{model}.onnx' for model in ('number', 'pos1', 'pos2', 'pos3')]
