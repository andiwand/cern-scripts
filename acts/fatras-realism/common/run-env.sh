#!/usr/bin/env bash
# Run a Python script with the local ACTS validation build and Geant4 data:
#   run-env.sh SCRIPT.py ARGS...
# Override ACTS_VALIDATION_BUILD, GEANT4_INSTALL or ACTS_PYTHON as needed.
set -o pipefail
validation_build=${ACTS_VALIDATION_BUILD:-$HOME/cern/build/acts/acts/dev3}
geant4=${GEANT4_INSTALL:-$HOME/cern/install/geant4/11.3.1}
data=$geant4/share/Geant4/data
source "$geant4/bin/geant4.sh"
source "$validation_build/this_acts_withdeps.sh"
export G4ENSDFSTATEDATA=$data/G4ENSDFSTATE3.0
export G4LEDATA=$data/G4EMLOW8.6.1
export G4LEVELGAMMADATA=$data/PhotonEvaporation6.1
export G4RADIOACTIVEDATA=$data/RadioactiveDecay6.1.2
export G4PARTICLEXSDATA=$data/G4PARTICLEXS4.1
export G4NEUTRONHPDATA=$data/G4NDL4.7.1
export G4PIIDATA=$data/G4PII1.3
export G4REALSURFACEDATA=$data/RealSurface2.2
export G4SAIDXSDATA=$data/G4SAIDDATA2.0
export G4ABLADATA=$data/G4ABLA3.3
export G4INCLDATA=$data/G4INCL1.2
set -e
export PYTHONDONTWRITEBYTECODE=1
exec "${ACTS_PYTHON:-$HOME/cern/source/acts/ci-dependencies/.spack-env/view/bin/python3}" "$@"
