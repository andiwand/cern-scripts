#include "ActsFatras/Physics/ElectroMagnetic/PhotonConversion.hpp"
#include "legacy-conversion.hpp"
#include <FTFP_BERT.hh>
#include <G4BetheHeitlerModel.hh>
#include <G4Box.hh>
#include <G4DynamicParticle.hh>
#include <G4Gamma.hh>
#include <G4LogicalVolume.hh>
#include <G4Material.hh>
#include <G4NistManager.hh>
#include <G4PVPlacement.hh>
#include <G4RunManager.hh>
#include <G4SystemOfUnits.hh>
#include <G4VUserDetectorConstruction.hh>
#include <Randomize.hh>
#include <chrono>
#include <fstream>
#include <random>
struct Detector : G4VUserDetectorConstruction {
  G4LogicalVolume *logical = nullptr;
  G4VPhysicalVolume *Construct() override {
    logical = new G4LogicalVolume(
        new G4Box("world", 1 * m, 1 * m, 1 * m),
        G4NistManager::Instance()->FindOrBuildMaterial("G4_Al"), "world");
    return new G4PVPlacement(nullptr, {}, logical, "world", nullptr, false, 0);
  }
};
struct Stats {
  std::array<unsigned, 50> fraction{};
  double angle = 0, depth = 0, energyError = 0;
  unsigned thin = 0;
  void add(double energy, double fraction1, double cosine, double error) {
    ++fraction[std::clamp(int(fraction1 * 50), 0, 49)];
    angle += std::acos(std::clamp(cosine, -1., 1.));
    energyError = std::max(energyError, std::abs(error) / energy);
  }
};
constexpr unsigned samples = 100000;
void output(std::ostream &out, const char *name, double energy, const Stats &s,
            double rate, double seconds, double thin = -1) {
  out << name << ',' << energy << ',' << samples << ',' << rate << ','
      << s.angle / samples << ',' << s.energyError << ','
      << (thin >= 0 ? thin : double(s.thin) / samples) << ',' << seconds;
  for (auto n : s.fraction)
    out << ',' << n;
  out << '\n';
}
template <typename Model>
void native(std::ostream &out, const char *name, double energy) {
  Model model;
  std::mt19937_64 rng(7742);
  ActsFatras::Particle photon(ActsFatras::Barcode().withParticle(1),
                              Acts::eGamma);
  photon.setAbsoluteMomentum(energy).setDirection(0, 0, 1);
  Stats s;
  auto start = std::chrono::steady_clock::now();
  for (unsigned i = 0; i < samples; ++i) {
    std::vector<ActsFatras::Particle> children;
    auto depth = model.generatePathLimits(rng, photon).first;
    s.depth += depth;
    s.thin += depth < 0.01;
    model.run(rng, photon, children);
    s.add(energy, children[0].energy() / energy, children[0].direction().z(),
          children[0].energy() + children[1].energy() - energy);
  }
  output(out, name, energy, s, samples / s.depth,
         std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
             .count());
}
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  G4Random::setTheSeed(7742);
  auto run = std::make_unique<G4RunManager>();
  auto *detector = new Detector;
  run->SetUserInitialization(detector);
  run->SetUserInitialization(new FTFP_BERT(0));
  run->Initialize();
  run->BeamOn(0);
  G4BetheHeitlerModel model;
  model.Initialise(G4Gamma::Gamma(), G4DataVector(1, 0));
  auto *material = detector->logical->GetMaterial();
  std::ofstream out(argv[1]);
  out << "model,energy_GeV,samples,rate_per_X0,mean_electron_angle,max_"
         "relative_energy_error,thin_001_X0_fraction,seconds";
  for (unsigned i = 0; i < 50; ++i)
    out << ",bin" << i;
  out << '\n';
  for (double energy : {0.002, 0.01, 0.1, 0.2, 1., 10., 100.}) {
    native<ActsFatras::PhotonConversion>(out, "corrected", energy);
    // The old fit is invalid at low energy. Keep that failure visible in rates.
    native<ActsFatras::LegacyPhotonConversion>(out, "legacy", energy);
    Stats s;
    auto start = std::chrono::steady_clock::now();
    G4DynamicParticle photon(G4Gamma::Gamma(), {0, 0, 1}, energy * GeV);
    for (unsigned i = 0; i < samples; ++i) {
      std::vector<G4DynamicParticle *> children;
      model.SampleSecondaries(&children,
                              detector->logical->GetMaterialCutsCouple(),
                              &photon, 0, energy * GeV);
      s.add(energy, children[0]->GetTotalEnergy() / (energy * GeV),
            children[0]->GetMomentumDirection().z(),
            (children[0]->GetTotalEnergy() + children[1]->GetTotalEnergy()) /
                    GeV -
                energy);
      for (auto *child : children)
        delete child;
    }
    const double rate =
        model.ComputeCrossSectionPerAtom(G4Gamma::Gamma(), energy * GeV, 13) *
        material->GetTotNbOfAtomsPerVolume() * material->GetRadlen();
    output(
        out, "geant4-Al", energy, s, rate,
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count(),
        -std::expm1(-0.01 * rate));
  }
}
