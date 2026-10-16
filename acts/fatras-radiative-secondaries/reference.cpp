#include "ActsFatras/Physics/ElectroMagnetic/Bremsstrahlung.hpp"

#include <array>
#include <cmath>
#include <iostream>

#include <G4Electron.hh>
#include <G4Material.hh>
#include <G4NistManager.hh>
#include <G4Positron.hh>
#include <G4SeltzerBergerModel.hh>
#include <G4SystemOfUnits.hh>
int main() {
  auto* nist = G4NistManager::Instance();
  for (auto name : {"G4_C", "G4_Si", "G4_Cu", "G4_Pb"})
    nist->FindOrBuildMaterial(name);
  std::cout << "material,pdg,kinetic_MeV,cut_MeV,g4_per_X0,native_per_X0\n";
  for (auto* p : std::array<const G4ParticleDefinition*, 2>{
           G4Electron::Definition(), G4Positron::Definition()}) {
    G4SeltzerBergerModel model(p);
    model.Initialise(p, {});
    for (auto name : {"G4_C", "G4_Si", "G4_Cu", "G4_Pb"}) {
      auto* mat = nist->FindOrBuildMaterial(name);
      for (double ke : {.2, .5, 1., 3., 10., 30., 100., 1000.}) {
        model.SetupForMaterial(p, mat, ke * MeV);
        for (double cut : {.1, 1., 10.}) {
          if (cut >= ke)
            continue;
          double rate =
              model.ComputeCrossSectionPerAtom(
                  p, ke * MeV, mat->GetZ(), mat->GetA(), cut * MeV, ke * MeV) *
              mat->GetTotNbOfAtomsPerVolume() * mat->GetRadlen();
          const auto native = Acts::Material::fromMassDensity(
              mat->GetRadlen() / mm * Acts::UnitConstants::mm,
              mat->GetNuclearInterLength() / mm * Acts::UnitConstants::mm,
              mat->GetA() / (g / mole), mat->GetZ(),
              mat->GetDensity() / (g / cm3) * Acts::UnitConstants::g /
                  Acts::UnitConstants::cm3);
          double analytic = 0;
          constexpr int bins = 4000;
          for (int i = 0; i < bins; ++i) {
            const double photon =
                cut * std::exp(std::log(ke / cut) * (i + .5) / bins);
            analytic += ActsFatras::Bremsstrahlung::spectrum(
                native, (ke + .51099895) * Acts::UnitConstants::MeV,
                photon * Acts::UnitConstants::MeV, p->GetPDGEncoding() == -11);
          }
          analytic *= std::log(ke / cut) / bins;
          std::cout << name << ',' << p->GetPDGEncoding() << ',' << ke << ','
                    << cut << ',' << rate << ',' << analytic << '\n';
        }
      }
    }
  }
}
