#!/usr/bin/env python3
"""Build the existing process-adapter benchmark on the same grid and G4 masses."""

import argparse
import subprocess
import sys
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--tools", type=Path, default=Path(__file__).resolve().parent.parent)
p.add_argument("--acts-source", type=Path, required=True)
p.add_argument("--acts-build", type=Path, required=True)
p.add_argument("--geant4-lib", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
source = (a.tools / "benchmark.cpp").read_text()
replacements = {
    "#include <FTFP_BERT.hh>": "#include <FTFP_BERT.hh>\n#include <G4ParticleTable.hh>",
    "{0.05, 0.2, 0.5, 2., 10., 100.}": "{0.05, 0.2, 0.5, 2., 4., 5., 6., 10., 100.}",
    ".setAbsoluteMomentum(p)": ".setMass(G4ParticleTable::GetParticleTable()->FindParticle(pdg)->GetPDGMass() / CLHEP::GeV)\n                .setAbsoluteMomentum(p)",
}
for before, after in replacements.items():
    if source.count(before) != 1:
        raise RuntimeError("Reference benchmark changed; review patch: " + before)
    source = source.replace(before, after)
a.output.parent.mkdir(parents=True, exist_ok=True)
path = a.output.with_suffix(".cpp")
path.write_text(source)
subprocess.run(
    [
        sys.executable,
        a.tools / "build-benchmark.py",
        "--source",
        path,
        "--output",
        a.output,
        "--acts-source",
        a.acts_source,
        "--acts-build",
        a.acts_build,
        "--geant4-lib",
        a.geant4_lib,
    ],
    check=True,
)
