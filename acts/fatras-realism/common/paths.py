"""Default locations of local builds and data; every one can be overridden.

Environment variables:
  FATRAS_DATA            data root (default ~/cern/data/fatras-realism)
  ACTS_VALIDATION_SOURCE ACTS source checkout
  ACTS_VALIDATION_BUILD  ACTS build directory (with compile_commands.json)
  GEANT4_LIB             directory with libG4*.dylib and libCLHEP.dylib
"""

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME = Path.home()
DATA = Path(os.environ.get("FATRAS_DATA", HOME / "cern/data/fatras-realism"))
SOURCE = Path(os.environ.get("ACTS_VALIDATION_SOURCE", HOME / "cern/source/acts/acts/dev3"))
BUILD = Path(os.environ.get("ACTS_VALIDATION_BUILD", HOME / "cern/build/acts/acts/dev3"))
GEANT4_LIB = Path(
    os.environ.get("GEANT4_LIB", HOME / "cern/source/acts/ci-dependencies/.spack-env/view/lib")
)
RUN_ENV = HERE / "run-env.sh"

# Reference inputs produced by earlier runs (see README "Setup").
INPUTS = DATA / "fatras-runtime-model/results/2026-10-15/inputs"
MATERIAL_MAP = DATA / "fatras-pion-validation/data/2026-10-14/odd-material-beampipe.root"
ID_WORLD = DATA / "fatras-charged-mesons/data/2026-10-14"
