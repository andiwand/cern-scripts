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

# Resolve exactly the configured models; the kernel checks itself against ONNX.
from pathlib import Path
from PathResolver import PathResolver
import hashlib

model = Path(
    PathResolver.FindCalibFile(
        flags.Acts.PixelNNCalibrationModelsFolder + "number.onnx"
    )
)
assert model.is_file()
os.environ["TAIL_SCORE_NATIVE_MODELS"] = str(model.parent)
for name in ["number", "pos1", "pos2", "pos3"]:
    path = model.with_name(name + ".onnx")
    print(
        "TAIL_SCORE_NATIVE_MODEL",
        str(path),
        hashlib.sha256(path.read_bytes()).hexdigest(),
    )
