#include "ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"
#include "G4BetheBlochModel.hh"
#include "G4Electron.hh"
#include "G4MollerBhabhaModel.hh"
#include "G4MuonMinus.hh"
#include "G4NistManager.hh"
#include "G4Positron.hh"
#include "G4Proton.hh"
#include <iostream>
#include <random>
int main() {
  using namespace Acts;
  using namespace Acts::UnitLiterals;
  using namespace ActsFatras;
  const auto *material =
      G4NistManager::Instance()->FindOrBuildMaterial("G4_Si");
  G4MollerBhabhaModel em;
  G4BetheBlochModel heavy;
  std::cout << "pdg,kinetic_MeV,cut_MeV,n,mean_electrons,g4_mean_electrons,"
               "mean_loss_MeV,g4_mean_loss_MeV,sem_loss_MeV\n";
  for (auto [pdg, definition] :
       std::array<std::pair<PdgParticle, G4ParticleDefinition *>, 4>{
           {{eElectron, G4Electron::Definition()},
            {ePositron, G4Positron::Definition()},
            {eMuon, G4MuonMinus::Definition()},
            {eProton, G4Proton::Definition()}}}) {
    for (double kinetic : {1., 10., 100., 1000.})
      for (double cut : {0.01, 0.1, 1.}) {
        if (kinetic <= 2 * cut)
          continue;
        auto *model = std::abs(pdg) == 11 ? static_cast<G4VEmModel *>(&em)
                                          : static_cast<G4VEmModel *>(&heavy);
        const double g4rate = model->CrossSectionPerVolume(
                                  material, definition, kinetic, cut, kinetic) *
                              0.01;
        const double g4loss = model->ComputeDEDXPerVolume(material, definition,
                                                          kinetic, kinetic) *
                              0.01;
        const MaterialSlab slab(ActsTests::makeSilicon(), 0.01_mm);
        Particle initial(Barcode().withParticle(1), pdg);
        initial.setAbsoluteMomentum(std::sqrt(
            kinetic * 1_MeV * (kinetic * 1_MeV + 2 * initial.mass())));
        std::mt19937_64 rng(42);
        constexpr int n = 1000000;
        double loss = 0, loss2 = 0;
        unsigned count = 0;
        for (int i = 0; i < n; ++i) {
          auto p = initial;
          count += Ionisation{cut * 1_MeV}(rng, slab, p).size();
          double l = (initial.energy() - p.energy()) / 1_MeV;
          loss += l;
          loss2 += l * l;
        }
        std::cout << pdg << ',' << kinetic << ',' << cut << ',' << n << ','
                  << double(count) / n << ',' << g4rate << ',' << loss / n
                  << ',' << g4loss << ','
                  << std::sqrt((loss2 / n - std::pow(loss / n, 2)) / n) << '\n';
      }
  }
}
