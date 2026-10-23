"""Inclusive results and timing repetitions, alongside pinned main and G4."""

import argparse
import importlib.util
import json
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
tools = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "gap", tools / "fatras-secondary-gap/analyse.py"
)
gap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gap)
previous = json.loads(
    (tools / "fatras-compton/results/2026-10-16/analysis.json").read_text()
)
r = {
    "runs": {
        "Previous": previous["runs"]["compton-100"],
        "Geant4": previous["runs"]["Geant4"],
    },
    "main": previous["main"],
    "archived_cpu": previous["archived_cpu"],
    "edges": gap.EDGES,
    "processes": gap.PROCESSES,
}
for name in ["current", "legacy-fixed"]:
    if (a.work / name / "metadata.json").exists():
        r["runs"][name] = gap.analyse(a.work / name)
r["timings"] = {}
for directory in sorted(a.work.iterdir()):
    if not (directory / "metadata.json").exists():
        continue
    m = json.loads((directory / "metadata.json").read_text())
    if "sequencer_cpu_seconds" not in m:
        continue
    r["timings"][directory.name] = {
        "cpu_s_per_event": m["sequencer_cpu_seconds"] / m["events"],
        "events": m["events"],
        "soft_physics": m.get("soft_physics"),
        "failures": m.get("navigation", {}).get("statistics", {}).get("failures"),
    }
(a.work / "analysis.json").write_text(json.dumps(r, indent=2))
