#!/usr/bin/env python3
"""Build (and optionally run) a standalone Fatras-versus-Geant4 reference program.

Kinds (sources in references/):
  ionisation    analytic ionisation vs Geant4                 -> WORK/ionisation.csv
  compton       Compton cross sections vs G4KleinNishinaModel -> WORK/compton.csv
  radiation     bremsstrahlung vs Geant4                      -> WORK/radiation.csv
  annihilation  positron annihilation vs G4eeToTwoGammaModel  -> WORK/annihilation.csv
  decay         native decay spectra vs Geant4 (run: WORK/decay-reference OUT.csv)
  slab          matched-material slab harness (driven by slab_scan.py)

The Fatras sources are compiled from --source, so the reference tests the
working tree, not the installed library. --run needs the Geant4 datasets:
  run-env.sh build_reference.py compton --work WORK --run
"""

import argparse
import subprocess
from pathlib import Path

import acts_compile
import paths

HERE = Path(__file__).resolve().parent
PHYSICS = "Fatras/src/Physics/"
KINDS = {
    "ionisation": ["Ionisation.cpp"],
    "compton": ["ComptonScattering.cpp"],
    "radiation": ["Bremsstrahlung.cpp"],
    "annihilation": [],
    "decay": [],
    "slab": ["Ionisation.cpp", "Bremsstrahlung.cpp", "ComptonScattering.cpp", "StandardInteractions.cpp"],
}


def build(kind, work, source=paths.SOURCE, build=paths.BUILD, geant4_lib=paths.GEANT4_LIB):
    work.mkdir(parents=True, exist_ok=True)
    output = work / ("slab" if kind == "slab" else f"{kind}-reference")
    acts_compile.build(
        record=work / f"{kind}-build.json",
        build=build,
        template="geant4-test",
        sources=[HERE / "references" / f"{kind}.cpp", *(source / PHYSICS / n for n in KINDS[kind])],
        output=output,
        acts=["ActsFatrasGeant4", "ActsFatras", "ActsCore"] if kind == "decay" else ["ActsFatras", "ActsCore"],
        geant4_lib=geant4_lib,
        clhep=True,
        source=source,
    )
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("kind", choices=KINDS)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--source", type=Path, default=paths.SOURCE)
    p.add_argument("--build", type=Path, default=paths.BUILD)
    p.add_argument("--geant4-lib", type=Path, default=paths.GEANT4_LIB)
    p.add_argument("--run", action="store_true", help="Write WORK/KIND.csv")
    a = p.parse_args()
    binary = build(a.kind, a.work.resolve(), a.source.resolve(), a.build.resolve(), a.geant4_lib)
    if a.run:
        csv = a.work / f"{a.kind}.csv"
        if a.kind == "slab":
            p.error("run the slab harness with slab_scan.py")
        if a.kind == "decay":
            subprocess.run([str(binary), str(csv)], check=True)
        else:
            with csv.open("w") as out:
                subprocess.run([str(binary)], stdout=out, check=True)
        print(csv)


if __name__ == "__main__":
    main()
