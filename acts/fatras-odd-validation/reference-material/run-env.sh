#!/usr/bin/env bash
set -o pipefail
validation_build=${ACTS_VALIDATION_BUILD:-/Users/andreas/cern/build/acts/acts/dev3}
source /Users/andreas/cern/install/geant4/11.3.1/bin/geant4.sh
source "$validation_build/this_acts_withdeps.sh"
export G4ENSDFSTATEDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4ENSDFSTATE3.0
export G4LEDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4EMLOW8.6.1
export G4LEVELGAMMADATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/PhotonEvaporation6.1
export G4RADIOACTIVEDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/RadioactiveDecay6.1.2
export G4PARTICLEXSDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4PARTICLEXS4.1
export G4NEUTRONHPDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4NDL4.7.1
export G4PIIDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4PII1.3
export G4REALSURFACEDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/RealSurface2.2
export G4SAIDXSDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4SAIDDATA2.0
export G4ABLADATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4ABLA3.3
export G4INCLDATA=/Users/andreas/cern/install/geant4/11.3.1/share/Geant4/data/G4INCL1.2
set -e
export PYTHONDONTWRITEBYTECODE=1
exec /Users/andreas/cern/source/acts/ci-dependencies/.spack-env/view/bin/python3 "$@"
