#!/usr/bin/env python3
"""Run a controlled charged-navigation ablation using the shared ODD runner."""

import argparse, hashlib, json, runpy, sys
from pathlib import Path

p = argparse.ArgumentParser(add_help=False)
p.add_argument("--transport-only", action="store_true")
p.add_argument("--module-dir", type=Path, required=True)
p.add_argument("--runner", type=Path, required=True)
p.add_argument("--try-all-pt-max", type=float, default=0.0)
p.add_argument("--far-limit-mm", type=float, default=10.0)
p.add_argument("--step-mm", type=float, default=10.0)
p.add_argument("--loop-fraction", type=float, default=0.5)
p.add_argument("--max-steps", type=int, default=1000)
p.add_argument("--charged-p-min", type=float, default=0.1)
p.add_argument("--charged-pt-min", type=float, default=0.05)
a, rest = p.parse_known_args()
assert (
    a.try_all_pt_max >= 0
    and a.far_limit_mm > 0
    and a.step_mm > 0
    and a.loop_fraction > 0
    and a.max_steps > 0
)
sys.path.insert(0, str(a.module_dir))
import acts.examples
import navigation_fatras

original = acts.examples.FatrasSimulation


def factory(**kwargs):
    cfg = original.Config()
    for k, v in kwargs.items():
        if k != "level":
            setattr(cfg, k, v)
    if a.transport_only:
        cfg.enableDecays = False
        cfg.nuclearInteractionTable = ""
        cfg.emScattering = False
        cfg.emEnergyLossIonisation = False
        cfg.emEnergyLossRadiation = False
        cfg.emPhotonConversion = False
    return navigation_fatras.make(
        cfg,
        a.try_all_pt_max,
        a.far_limit_mm,
        a.step_mm,
        a.loop_fraction,
        a.max_steps,
        a.charged_p_min,
        a.charged_pt_min,
    )


acts.examples.FatrasSimulation = factory
sys.argv = [str(a.runner), *rest]
output = Path(rest[rest.index("--output") + 1])
settings = {k: str(v) if isinstance(v, Path) else v for k, v in vars(a).items()}
settings["module_sha256"] = hashlib.sha256(
    (a.module_dir / "navigation_fatras.so").read_bytes()
).hexdigest()
settings["dispatch"] = (
    "TryAll for initial charged-particle pT below threshold; otherwise standard Navigator. Neutral transport unchanged."
)
try:
    runpy.run_path(str(a.runner), run_name="__main__")
finally:
    if output.exists():
        settings["statistics"] = dict(navigation_fatras.statistics())
        (output / "navigation-audit.json").write_text(
            json.dumps(settings, indent=2) + "\n"
        )
        if (output / "metadata.json").exists():
            meta = json.loads((output / "metadata.json").read_text())
            meta["charged_navigation_experiment"] = settings
            if a.transport_only:
                meta["physics"] = "Transport only: no material interactions, no decays"
                meta["table"] = None
                meta["table_sha256"] = None
            (output / "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
