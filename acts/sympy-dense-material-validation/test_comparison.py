"""Regression checks for the thesis dense-propagation comparison helpers."""

import argparse
import importlib.util
from pathlib import Path
import tempfile
import numpy as np
import scipy.stats
import uproot

parser = argparse.ArgumentParser()
parser.add_argument("--thesis", type=Path, default=Path.home() / "cern/thesis")
args = parser.parse_args()
path = args.thesis / "scripts/dense-propagation/common.py"
spec = importlib.util.spec_from_file_location("dense_comparison", path)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

normal = np.random.default_rng(20261031).normal(size=1_000_000)
(_, sigma), _ = common.robust_gauss_fit(normal)
assert abs(sigma - 1) < 0.005, sigma
for loc in [-3, 0, 10]:
    for scale in [0.1, 1, 5]:
        left, right = common.fwhm_landau(loc, scale)
        peak = loc + scale * common._LANDAU_MODE
        half = scipy.stats.landau.pdf(peak, loc, scale) / 2
        np.testing.assert_allclose(
            scipy.stats.landau.pdf([left, right], loc, scale), half, rtol=1e-8
        )

old = args.thesis / "data/dense-propagation/geant4/single_mom_1GeV_lar_1000mm.root"
legacy = common.read_g4_data(old, 0)
mass = 0.1056583755
np.testing.assert_allclose(
    legacy.p_initial,
    np.sqrt(legacy.kinetic_initial * (legacy.kinetic_initial + 2 * mass)),
)
with tempfile.TemporaryDirectory() as directory:
    new = Path(directory) / "reading.root"
    with uproot.recreate(new) as f:
        f["reading"] = {
            "p_initial": np.array([2.0]),
            "p_final": np.array([1.5]),
            "kinetic_initial": np.array([1.897]),
            "kinetic_final": np.array([1.398]),
        }
    values = common.read_g4_data(new, 1.4)
    assert values.p_initial.iloc[0] == 2 and values.p_final.iloc[0] == 1.5
    assert len(common.read_g4_data(new, 1.6)) == 0
print(
    f"PASS Gaussian sigma={sigma:.9f}; Landau half-height roots; legacy/new schemas; momentum cuts"
)
