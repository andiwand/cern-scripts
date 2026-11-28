"""All-charge pixel NN; primary only, identical seed and tracking settings."""

import os
from ActsConfig.ActsMeasurementCalibrationConfig import ActsNNClusteringToolCfg

mode = os.environ.get("NN_MODE", "pre")
assert mode in ("pre", "post")
a = cfg.getEventAlgo("ActsTrackFindingAlg")
a.PixelCalibrator = cfg.popToolsAndMerge(
    ActsNNClusteringToolCfg(
        flags,
        name="TailScoreNN",
        CalibrateAfterMeasurementSelection=mode == "post",
        minClusterChargeForNN=0.0,
        minClusterSizeForNN=0,
    )
)
print("TAIL_SCORE_NN", mode, "charge=0 size=0", "forceTrackOnSeed", a.forceTrackOnSeed)
