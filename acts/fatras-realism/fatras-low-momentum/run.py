"""Single-worker, fixed-geometry navigation probe around the common ODD runner."""

import argparse, json, runpy, sys
from pathlib import Path

p = argparse.ArgumentParser(add_help=False)
p.add_argument("--navigation-mode", type=int, choices=[0, 1, 2], default=0)
p.add_argument("--navigation-pt-max", type=float, default=0.5)
p.add_argument("--navigation-step", type=float, default=5)
p.add_argument("--loops", type=float, default=4)
p.add_argument("--max-steps", type=int, default=5000)
p.add_argument("--p-min", type=float, default=0.02)
p.add_argument("--pt-min", type=float, default=0.005)
p.add_argument("--transport-only", action="store_true")
p.add_argument(
    "--runner",
    type=Path,
    default=Path(__file__).resolve().parent.parent / "fatras-runtime-model/run.py",
)
a, rest = p.parse_known_args()


def value(name, default=None):
    return rest[rest.index(name) + 1] if name in rest else default


if (
    value("--threads", "1") != "1"
    or value("--mode") != "live"
    or not value("--module-dir")
):
    p.error("prototype requires live mode, module-dir and one worker")
if (
    min(a.navigation_step, a.loops, a.max_steps) <= 0
    or min(a.navigation_pt_max, a.p_min, a.pt_min) < 0
):
    p.error("invalid transport settings")
sys.path.insert(0, value("--module-dir"))
import acts.examples
import runtime_fatras

original = runtime_fatras.make


def make(cfg, live):
    cfg.pMin = a.p_min
    cfg.pTMin = a.pt_min
    if a.transport_only:
        cfg.enableDecays = False
        cfg.emScattering = False
        cfg.emEnergyLossIonisation = False
        cfg.emEnergyLossRadiation = False
        cfg.emPhotonConversion = False
    return original(
        cfg,
        live and not a.transport_only,
        a.navigation_mode,
        a.navigation_pt_max,
        a.navigation_step,
        a.loops,
        a.max_steps,
    )


runtime_fatras.make = make
sys.argv = [str(a.runner), *rest]
runpy.run_path(str(a.runner), run_name="__main__")
path = Path(value("--output")) / "metadata.json"
metadata = json.loads(path.read_text())
metadata["p_min_GeV"] = a.p_min
metadata["pt_min_GeV"] = a.pt_min
metadata["navigation"] = {
    "mode": a.navigation_mode,
    "pt_max_GeV": a.navigation_pt_max,
    "step_mm": a.navigation_step,
    "loops": a.loops,
    "max_steps": a.max_steps,
    "transport_only": a.transport_only,
    "statistics": dict(runtime_fatras.statistics()),
}
if a.transport_only:
    metadata["physics"] = "Transport only; no decays or material interactions"
path.write_text(json.dumps(metadata, indent=2))
