"""Collect event-level means/standard errors and validate the slab experiment."""

import argparse, csv, hashlib, json, math
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
w = a.work
records = []
for phase in ["runs", "refined", "attribution"]:
    files = sorted((w / phase).glob("*.json"))
    assert len(files) == {"runs": 232, "refined": 40, "attribution": 5}[phase], (
        phase,
        len(files),
    )
    for meta in files:
        d = json.loads(meta.read_text())
        d["phase"] = phase
        d["file"] = str(meta.with_suffix(".csv").relative_to(w))
        d["metrics"] = {}
        for row in csv.DictReader(meta.with_suffix(".csv").open()):
            assert int(row["n"]) == d["n"]
            v = {key: float(row[key]) for key in ["mean", "sem"]}
            assert all(math.isfinite(x) and x >= 0 for x in v.values()), meta
            d["metrics"][row["metric"]] = v
        if d["backend"] == "g4":
            assert "CUTS_MeV 0.1 0.1 0.1" in meta.with_suffix(".log").read_text()
        if d["profile"] == "common":
            assert all(
                d["metrics"][k]["mean"] == 0 for k in ["photoelectric", "annihilation"]
            )
        assert d["metrics"]["escape_energy_MeV"]["mean"] <= d["energy_MeV"] * (
            1 + 1e-6
        ), meta
        records.append(d)
(w / "analysis.json").write_text(
    json.dumps(
        {
            "records": records,
            "checks": {
                "settings": len(records),
                "primary_trials": sum(r["n"] for r in records),
                "finite_nonnegative_metrics": True,
                "matched_g4_cuts": True,
                "disabled_mechanisms_absent": True,
                "mean_escape_energy_bounded": True,
            },
            "notes": [
                "Particle production/escape counts above 100 keV are diagnostic, not ODD hit counts.",
                "Common: ionisation, brems, conversion, Compton; multiple scattering off.",
                "Extended: common plus photoelectric and annihilation, multiple scattering off.",
                "Full: G4EmStandardPhysics; Fatras additionally enables its existing multiple scattering.",
                "Fatras remaining-column bookkeeping is reused from SimulationActor. No material or ACTS source change.",
                "Slab subdivision changes the electron multiple-scattering approximation; full-profile fine slicing is a sensitivity study, not a converged solution.",
            ],
        },
        indent=2,
    )
)
print(
    len(records),
    "settings;",
    sum(r["n"] for r in records),
    "primary trials; checks passed",
)
