#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/BoundTrackParameters.hpp"
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Material/HomogeneousVolumeMaterial.hpp"
#include "Acts/Material/Interactions.hpp"
#include "Acts/Propagator/SympyStepper.hpp"
#include "Acts/Propagator/detail/MaterialEffectsAccumulator.hpp"
#include "Acts/Propagator/detail/SympyBoundToFreeScaling.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"
#include "FTFP_BERT.hh"
#include "G4BetheBlochModel.hh"
#include "G4Box.hh"
#include "G4EmCalculator.hh"
#include "G4LogicalVolume.hh"
#include "G4MuBetheBlochModel.hh"
#include "G4MuBremsstrahlungModel.hh"
#include "G4MuPairProductionModel.hh"
#include "G4MuonMinus.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4VUserDetectorConstruction.hh"
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
using namespace Acts;
using namespace Acts::UnitLiterals;

class Detector : public G4VUserDetectorConstruction {
public:
  G4VPhysicalVolume *Construct() override {
    auto *nist = G4NistManager::Instance();
    auto *world =
        new G4LogicalVolume(new G4Box("world", 2000, 2000, 2000),
                            nist->FindOrBuildMaterial("G4_Galactic"), "world");
    int i = 0;
    for (auto name : {"G4_Fe", "G4_lAr", "G4_Si"}) {
      auto *lv = new G4LogicalVolume(new G4Box(name, 10, 10, 10),
                                     nist->FindOrBuildMaterial(name), name);
      new G4PVPlacement(nullptr, G4ThreeVector(100 * i++, 0, 0), lv, name,
                        world, false, 0);
    }
    return new G4PVPlacement(nullptr, {}, world, "world", nullptr, false, 0);
  }
};

double integrate(double p, double mass, double length, double h,
                 const std::function<double(double)> &stopping) {
  double e = std::hypot(p, mass);
  const int n = std::ceil(length / h);
  h = length / n;
  auto f = [&](double energy) {
    return -stopping(std::sqrt(energy * energy - mass * mass));
  };
  for (int i = 0; i < n; ++i) {
    double a = f(e), b = f(e + h * a / 2), c = f(e + h * b / 2),
           d = f(e + h * c);
    e += h * (a + 2 * b + 2 * c + d) / 6;
  }
  return std::sqrt(e * e - mass * mass);
}

int main(int argc, char **argv) {
  const std::string output = argc > 1 ? argv[1] : ".";
  G4RunManager manager;
  manager.SetUserInitialization(new Detector());
  manager.SetUserInitialization(new FTFP_BERT(0));
  manager.Initialize();
  manager.BeamOn(0);
  G4EmCalculator calculator;
  G4BetheBlochModel plainBethe;
  G4DataVector cuts(2, DBL_MAX);
  plainBethe.Initialise(G4MuonMinus::Definition(), cuts);
  auto *mu = G4MuonMinus::Definition();
  double mass = ParticleHypothesis::muon().mass();
  std::ofstream out(output + "/rates.csv");
  out << std::setprecision(15)
      << "material,p,acts,g4,matched_density,matched_density_I,delta_acts,"
         "delta_g4,I_acts,I_g4,g4_plain_bethe\n";
  std::ofstream trajectory(output + "/g4ion-covariance.csv");
  trajectory << std::setprecision(15)
             << "material,p,pout,angle_sigma,exit_sigma,screen_sigma\n";
  for (auto [name, mat] : std::vector<std::pair<std::string, Material>>{
           {"Fe", ActsTests::makeIron()},
           {"lAr", ActsTests::makeLiquidArgon()}}) {
    auto *g4 = G4NistManager::Instance()->FindOrBuildMaterial("G4_" + name);
    auto *ion = g4->GetIonisation();
    double I = ion->GetMeanExcitationEnergy() / CLHEP::GeV;
    for (double p : {.5, 1., 1.05, 1.06, 2., 2.6, 3., 4., 10., 100., 300.}) {
      double bg = p / mass, beta2 = p * p / (p * p + mass * mass),
             Iacts = mat.meanExcitationEnergy();
      double plasma =
          28.816e-9 * std::sqrt(mat.molarElectronDensity() / (1 / 1_cm3));
      double da = bg < 10 ? 0
                          : 2 * (std::log(bg) + std::log(plasma / Iacts) - .5),
             dg = ion->DensityCorrection(std::log10(bg));
      double eps = .5 * .307075e-3 * mat.molarElectronDensity() / (1 / 1_cm3) /
                   10 / beta2;
      double act =
          computeEnergyLossBethe(MaterialSlab(mat, 1_mm), mass, -1 / p, 1);
      double density = act + eps * (da - dg);
      double matched = density + 2 * eps * std::log(Iacts / I);
      double kinetic = (std::hypot(p, mass) - mass) / 1_MeV;
      out << name << ',' << p << ',' << act / 1_MeV << ','
          << calculator.ComputeDEDX(kinetic, mu, "muIoni", g4, DBL_MAX) << ','
          << density / 1_MeV << ',' << matched / 1_MeV << ',' << da << ',' << dg
          << ',' << Iacts / 1_eV << ',' << I / 1_eV << ','
          << plainBethe.ComputeDEDXPerVolume(g4, mu, kinetic, DBL_MAX) << '\n';
    }
    for (double p0 : {4., 10., 100.}) {
      const auto particle = ParticleHypothesis::muon();
      detail::MaterialEffectsAccumulator acc;
      acc.initialize(.01, particle, p0);
      double energy = std::hypot(p0, mass), p = p0;
      const double h = .1;
      auto f = [&](double e) {
        return -calculator.ComputeDEDX((e - mass) / 1_MeV, mu, "muIoni", g4,
                                       DBL_MAX) *
               1_MeV;
      };
      for (int i = 0; i < 10000; ++i) {
        double k1 = f(energy), k2 = f(energy + h * k1 / 2),
               k3 = f(energy + h * k2 / 2), k4 = f(energy + h * k3);
        energy += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6;
        double pn = std::sqrt(energy * energy - mass * mass);
        acc.accumulate(mat, h, -1 / p, -1 / pn);
        p = pn;
      }
      auto cov = acc.computeAdditionalFreeCovariance(Vector3::UnitX()).value();
      double drift = 1000;
      double sv = cov(eFreePos1, eFreePos1) +
                  2 * drift * cov(eFreePos1, eFreeDir1) +
                  drift * drift * cov(eFreeDir1, eFreeDir1);
      trajectory << name << ',' << p0 << ',' << p << ','
                 << std::sqrt(cov(eFreeDir1, eFreeDir1)) << ','
                 << std::sqrt(cov(eFreePos1, eFreePos1)) << ',' << std::sqrt(sv)
                 << '\n';
    }
  }
}
