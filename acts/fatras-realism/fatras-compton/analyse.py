"""Reuse inclusive accounting and retain provenance for every run."""

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
old = json.loads(
    (tools / "fatras-secondary-gap/results/2026-10-16/summary.json").read_text()
)
result = {
    "edges": gap.EDGES,
    "processes": gap.PROCESSES,
    "runs": {"Control": old["runs"]["Fatras"], "Geant4": old["runs"]["Geant4"]},
}
for name in ["compton-100", "compton-50", "compton-200", "compton-pair-cut"]:
    if (a.work / name / "metadata.json").exists():
        result["runs"][name] = gap.analyse(a.work / name)
main = json.loads(
    (tools / "fatras-soft-secondaries/results/2026-10-15/summary.json").read_text()
)
result["main"] = main["summary"]["ACTS main"]
result["main_metadata"] = main["runs"]["ACTS main"]["metadata"]
result["archived_cpu"] = {
    "ACTS main": main["summary"]["ACTS main"]["cpu_s_per_event"],
    "Geant4": main["summary"]["Geant4 default, ID only"]["cpu_s_per_event"],
    "Control": 11.388162333333333,
}
result["timings"] = {}
for directory in sorted(a.work.iterdir()):
    if not (directory / "metadata.json").exists():
        continue
    meta = json.loads((directory / "metadata.json").read_text())
    result["timings"][directory.name] = {
        "cpu_s_per_event": meta["sequencer_cpu_seconds"] / meta["events"],
        "events": meta["events"],
        "soft_physics": meta.get("soft_physics"),
        "failures": meta.get("navigation", {}).get("statistics", {}).get("failures"),
        "standard": "navigation" not in meta,
    }
(a.work / "analysis.json").write_text(json.dumps(result, indent=2))
