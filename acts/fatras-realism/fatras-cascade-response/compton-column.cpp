#include "ActsFatras/Physics/ElectroMagnetic/ComptonScattering.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"
#include <iostream>
#include <random>
int main() {
  using namespace Acts;
  using namespace ActsFatras;
  std::cout << "energy_MeV,thickness_mm,slices,n,scatter_mean,recoil_above_"
               "40keV_mean,exit_MeV\n";
  for (double e : {.2, 1., 5., 20.})
    for (double thickness : {.3, 3., 30.})
      for (int slices : {1, 100, 1000}) {
        std::mt19937_64 rng(42);
        const int n = 10000;
        double count = 0, accepted = 0, exit = 0;
        MaterialSlab slab(ActsTests::makeSilicon(), thickness / slices);
        for (int i = 0; i < n; ++i) {
          Particle p(Barcode().withParticle(1), eGamma);
          p.setAbsoluteMomentum(e * UnitConstants::MeV);
          std::vector<Particle> children;
          for (int j = 0; j < slices && p.energy() > .1 * UnitConstants::MeV;
               ++j) {
            children.clear();
            if (ComptonScattering{}(rng, slab, p, children)) {
              ++count;
              accepted += (children[0].energy() - children[0].mass()) >=
                          .04 * UnitConstants::MeV;
              p = children[1];
            }
          }
          exit += p.energy() / UnitConstants::MeV;
        }
        std::cout << e << ',' << thickness << ',' << slices << ',' << n << ','
                  << count / n << ',' << accepted / n << ',' << exit / n
                  << '\n';
      }
}
