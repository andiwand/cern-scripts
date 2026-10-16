#include "ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp"
#include "G4Electron.hh"
#include "G4MollerBhabhaModel.hh"
#include "G4NistManager.hh"
#include "G4Positron.hh"
#include "G4SystemOfUnits.hh"
#include <iostream>
#include <random>
int main() {
  using namespace Acts;
  using namespace ActsFatras;
  std::cout << "material,pdg,kinetic_MeV,range_mm,thickness_mm,slices,n,delta_"
               "mean,delta_sem,exit_MeV,stop_fraction,g4_csda_delta\n";
  for (auto name : {"G4_Si", "G4_Cu"}) {
    auto *mat = G4NistManager::Instance()->FindOrBuildMaterial(name);
    auto native = Material::fromMassDensity(
        mat->GetRadlen() / mm, mat->GetNuclearInterLength() / mm,
        mat->GetA() / (g / mole), mat->GetZ(),
        mat->GetDensity() / (g / cm3) * UnitConstants::g / UnitConstants::cm3);
    for (auto pdg : {eElectron, ePositron}) {
      auto *def =
          pdg == eElectron
              ? static_cast<G4ParticleDefinition *>(G4Electron::Definition())
              : G4Positron::Definition();
      G4MollerBhabhaModel model(def);
      for (double ke : {.3, 1., 5., 20.}) {
        double range = 0, delta = 0;
        const double emin = .001;
        const int bins = 20000;
        for (int i = 0; i < bins; ++i) {
          double e = emin * std::exp(std::log(ke / emin) * (i + .5) / bins);
          double de = e * std::log(ke / emin) / bins;
          double dedx = model.ComputeDEDXPerVolume(mat, def, e, e);
          range += de / dedx;
          delta += de / dedx * model.CrossSectionPerVolume(mat, def, e, .1, e);
        }
        for (double fraction : {.1, 1., 3.})
          for (int slices : {1, 100, 1000}) {
            std::mt19937_64 rng(42);
            double sum = 0, sum2 = 0, exit = 0, stopped = 0;
            const int n = 2000;
            for (int i = 0; i < n; ++i) {
              Particle p(Barcode().withParticle(1), pdg);
              p.setAbsoluteMomentum(
                  std::sqrt(ke * UnitConstants::MeV *
                            (ke * UnitConstants::MeV + 2 * p.mass())));
              unsigned count = 0;
              MaterialSlab slab(native, range * fraction / slices);
              for (int j = 0; j < slices && p.isAlive(); ++j)
                count += Ionisation{}(rng, slab, p).size();
              sum += count;
              sum2 += count * count;
              exit += (p.energy() - p.mass()) / UnitConstants::MeV;
              stopped += !p.isAlive();
            }
            std::cout << name << ',' << int(pdg) << ',' << ke << ',' << range
                      << ',' << range * fraction << ',' << slices << ',' << n
                      << ',' << sum / n << ','
                      << std::sqrt((sum2 / n - sum * sum / n / n) / n) << ','
                      << exit / n << ',' << stopped / n << ',' << delta << '\n';
          }
      }
    }
  }
}
