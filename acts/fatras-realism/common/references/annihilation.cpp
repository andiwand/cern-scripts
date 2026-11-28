#include "ActsFatras/Physics/ElectroMagnetic/PositronAnnihilation.hpp"
#include "G4DynamicParticle.hh"
#include "G4Positron.hh"
#include "G4SystemOfUnits.hh"
#include "G4eeToTwoGammaModel.hh"
#include "Randomize.hh"
#include <iomanip>
#include <iostream>
int main() {
  G4eeToTwoGammaModel model;
  model.Initialise(G4Positron::Definition(), {});
  std::mt19937_64 rng(19);
  G4Random::setTheSeed(19);
  std::cout << "kinetic_MeV,native_mm2,g4_mm2,native_mean_asymmetry,g4_mean_"
               "asymmetry\n"
            << std::setprecision(12);
  for (double k : {.000001, .001, .1, 1., 20., 100., 1000.}) {
    double n = 0, g = 0;
    for (unsigned i = 0; i < 100000; ++i) {
      ActsFatras::Particle p(ActsFatras::Barcode().withParticle(1),
                             Acts::ePositron);
      const double ke = k * Acts::UnitConstants::MeV;
      p.setAbsoluteMomentum(std::sqrt(ke * (ke + 2 * p.mass())))
          .setDirection(0, 0, 1);
      std::vector<ActsFatras::Particle> out;
      ActsFatras::PositronAnnihilation{}.annihilate(rng, p, out);
      n += std::abs(out[0].energy() - out[1].energy()) /
           (out[0].energy() + out[1].energy());
      G4DynamicParticle gp(G4Positron::Definition(), G4ThreeVector(0, 0, 1),
                           k * MeV);
      std::vector<G4DynamicParticle *> go;
      model.SampleSecondaries(&go, nullptr, &gp, 0, 0);
      g += std::abs(go[0]->GetTotalEnergy() - go[1]->GetTotalEnergy()) /
           (go[0]->GetTotalEnergy() + go[1]->GetTotalEnergy());
      for (auto *q : go)
        delete q;
    }
    std::cout << k << ','
              << ActsFatras::PositronAnnihilation::crossSection(
                     k * Acts::UnitConstants::MeV)
              << ','
              << model.ComputeCrossSectionPerElectron(k * MeV) / (mm * mm)
              << ',' << n / 100000 << ',' << g / 100000 << '\n';
  }
}
