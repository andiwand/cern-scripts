#include "ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp"
#include "G4Gamma.hh"
#include "G4KleinNishinaModel.hh"
#include "G4SystemOfUnits.hh"
#include <iomanip>
#include <iostream>
int main() {
  G4KleinNishinaModel model;
  std::cout << std::setprecision(12) << "Z,energy_MeV,native_barn,g4_barn\n";
  for (double z : {4., 6., 13., 14., 22., 29., 82.})
    for (double e :
         {.01, .03, .05, .1, .2, .5, 1., 3., 10., 100., 1000., 100000.}) {
      const double native =
          ActsFatras::ComptonScattering::crossSection(
              e * Acts::UnitConstants::MeV) *
          z / (1e-22 * Acts::UnitConstants::mm * Acts::UnitConstants::mm);
      const double g4 = model.ComputeCrossSectionPerAtom(G4Gamma::Definition(),
                                                         e * MeV, z, 0, 0, 0) /
                        barn;
      std::cout << z << ',' << e << ',' << native << ',' << g4 << '\n';
    }
}
