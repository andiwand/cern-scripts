// Diagnostic homogeneous-slab comparison. No ACTS production changes.
#include "ActsFatras/Kernel/detail/SimulationActor.hpp"
#include "ActsFatras/Physics/StandardInteractions.hpp"

#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include "G4Box.hh"
#include "G4Electron.hh"
#include "G4EmParameters.hh"
#include "G4EmStandardPhysics.hh"
#include "G4Gamma.hh"
#include "G4LogicalVolume.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4Positron.hh"
#include "G4ProcessManager.hh"
#include "G4ProductionCuts.hh"
#include "G4ProductionCutsTable.hh"
#include "G4RToEConvForElectron.hh"
#include "G4RToEConvForGamma.hh"
#include "G4RToEConvForPositron.hh"
#include "G4Region.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserEventAction.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VModularPhysicsList.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"

constexpr double cutMeV = .1;
const std::array<const char*, 11> names = {"brems",
                                           "ionisation",
                                           "compton",
                                           "conversion",
                                           "photoelectric",
                                           "annihilation",
                                           "escape_gamma",
                                           "escape_charged",
                                           "escape_energy_MeV",
                                           "primary_exit_MeV",
                                           "compton_scatter"};
using Event = std::array<double, 11>;
struct Scores {
  Event event{}, sum{}, sum2{};
  int n = 0;
  void finish() {
    for (int k = 0; k < 11; ++k) {
      sum[k] += event[k];
      sum2[k] += event[k] * event[k];
    }
    event = {};
    ++n;
  }
} scores;
struct Config {
  std::string backend, material, profile, mode, output;
  int pdg, n, slices;
  double energy, thickness;
  long seed;
} cfg;
void birth(int pdg, double ke, const std::string& process) {
  if (process == "compt" && pdg == 11)
    ++scores.event[10];
  if (ke < cutMeV * (1 - 1e-9))
    return;
  int k = -1;
  if (process == "eBrem" && pdg == 22)
    k = 0;
  if (process == "eIoni" && pdg == 11)
    k = 1;
  if (process == "compt" && pdg == 11)
    k = 2;
  if (process == "conv" && std::abs(pdg) == 11)
    k = 3;
  if (process == "phot" && pdg == 11)
    k = 4;
  if (process == "annihil" && pdg == 22)
    k = 5;
  if (k >= 0)
    ++scores.event[k];
}
void escape(int pdg, double ke, bool primary) {
  if (primary)
    scores.event[9] += ke;
  if (ke >= cutMeV * (1 - 1e-9)) {
    if (pdg == 22)
      ++scores.event[6];
    else if (std::abs(pdg) == 11)
      ++scores.event[7];
    scores.event[8] += ke;
  }
}
class Detector : public G4VUserDetectorConstruction {
 public:
  G4Material* mat = nullptr;
  G4VPhysicalVolume* Construct() override {
    auto* n = G4NistManager::Instance();
    mat = n->FindOrBuildMaterial(cfg.material);
    auto* wl =
        new G4LogicalVolume(new G4Box("world", 100 * m, 100 * m, 100 * m),
                            n->FindOrBuildMaterial("G4_Galactic"), "world");
    auto* w = new G4PVPlacement(nullptr, {}, wl, "world", nullptr, false, 0);
    auto* sl = new G4LogicalVolume(
        new G4Box("slab", 50 * m, 50 * m, cfg.thickness * mm / 2), mat, "slab");
    new G4PVPlacement(nullptr, {0, 0, cfg.thickness * mm / 2}, sl, "slab", wl,
                      false, 0);
    return w;
  }
};
class Physics : public G4VModularPhysicsList {
 public:
  Physics() {
    SetVerboseLevel(0);
    RegisterPhysics(new G4EmStandardPhysics(0));
  }
  void SetCuts() override {
    auto* mat = G4NistManager::Instance()->FindOrBuildMaterial(cfg.material);
    auto* table = G4ProductionCutsTable::GetProductionCutsTable();
    table->SetEnergyRange(100 * eV, 100 * GeV);
    G4RToEConvForGamma gamma;
    G4RToEConvForElectron electron;
    G4RToEConvForPositron positron;
    for (auto* particle :
         {static_cast<G4ParticleDefinition*>(G4Gamma::Definition()),
          static_cast<G4ParticleDefinition*>(G4Electron::Definition()),
          static_cast<G4ParticleDefinition*>(G4Positron::Definition())}) {
      G4VRangeToEnergyConverter* converter =
          particle == G4Gamma::Definition()
              ? static_cast<G4VRangeToEnergyConverter*>(&gamma)
          : particle == G4Electron::Definition()
              ? static_cast<G4VRangeToEnergyConverter*>(&electron)
              : static_cast<G4VRangeToEnergyConverter*>(&positron);
      double lo = 1e-9 * mm, hi = 1e6 * mm;
      for (int i = 0; i < 100; ++i) {
        double r = std::sqrt(lo * hi);
        if (converter->Convert(r, mat) < cutMeV * MeV)
          lo = r;
        else
          hi = r;
      }
      SetCutValue(std::sqrt(lo * hi), particle->GetParticleName());
    }
  }
};
class Gun : public G4VUserPrimaryGeneratorAction {
  G4ParticleGun gun{1};

 public:
  Gun() {
    gun.SetParticleDefinition(
        G4ParticleTable::GetParticleTable()->FindParticle(cfg.pdg));
    gun.SetParticleEnergy(cfg.energy * MeV);
    gun.SetParticlePosition({0, 0, 1e-6 * mm});
    gun.SetParticleMomentumDirection({0, 0, 1});
  }
  void GeneratePrimaries(G4Event* e) override { gun.GeneratePrimaryVertex(e); }
};
class EventAction : public G4UserEventAction {
  void EndOfEventAction(const G4Event*) override { scores.finish(); }
};
class Stack : public G4UserStackingAction {
  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track* t) override {
    if (t->GetParentID() == 0)
      return fUrgent;
    if (auto* p = t->GetCreatorProcess())
      birth(t->GetDefinition()->GetPDGEncoding(), t->GetKineticEnergy() / MeV,
            p->GetProcessName());
    if (cfg.mode == "primary")
      return fKill;
    if (t->GetDefinition() == G4Gamma::Definition() &&
        t->GetKineticEnergy() < cutMeV * MeV)
      return fKill;
    return fUrgent;
  }
};
class Steps : public G4UserSteppingAction {
  void UserSteppingAction(const G4Step* step) override {
    auto* t = step->GetTrack();
    auto* pre = step->GetPreStepPoint()->GetPhysicalVolume();
    auto* post = step->GetPostStepPoint()->GetPhysicalVolume();
    if (pre && pre->GetName() == "slab" &&
        (!post || post->GetName() != "slab")) {
      escape(t->GetDefinition()->GetPDGEncoding(), t->GetKineticEnergy() / MeV,
             t->GetParentID() == 0);
      t->SetTrackStatus(fStopAndKill);
    }
    if (t->GetDefinition() == G4Gamma::Definition() &&
        t->GetKineticEnergy() < cutMeV * MeV)
      t->SetTrackStatus(fStopAndKill);
  }
};
void geant() {
  auto* run = new G4RunManager;
  auto* det = new Detector;
  run->SetUserInitialization(det);
  run->SetUserInitialization(new Physics);
  G4EmParameters::Instance()->SetGeneralProcessActive(false);
  run->Initialize();
  if (cfg.profile != "full")
    for (auto* def :
         {static_cast<G4ParticleDefinition*>(G4Gamma::Definition()),
          static_cast<G4ParticleDefinition*>(G4Electron::Definition()),
          static_cast<G4ParticleDefinition*>(G4Positron::Definition())}) {
      auto* pm = def->GetProcessManager();
      auto* processList = pm->GetProcessList();
      for (int i = 0; i < pm->GetProcessListLength(); ++i) {
        auto name = (*processList)[i]->GetProcessName();
        if (name == "msc" ||
            (name == "phot" &&
             (cfg.profile == "common" || cfg.profile == "annihilation")) ||
            (name == "annihil" &&
             (cfg.profile == "common" || cfg.profile == "photoelectric")))
          pm->SetProcessActivation((*processList)[i], false);
      }
    }
  run->SetUserAction(new Gun);
  run->SetUserAction(new Stack);
  run->SetUserAction(new Steps);
  run->SetUserAction(new EventAction);
  G4Random::setTheSeed(cfg.seed);
  run->BeamOn(cfg.n);
  auto* ct = G4ProductionCutsTable::GetProductionCutsTable();
  bool foundCuts = false;
  for (std::size_t j = 0; j < ct->GetTableSize(); ++j)
    if (ct->GetMaterialCutsCouple(j)->GetMaterial() == det->mat) {
      foundCuts = true;
      std::cerr << "CUTS_MeV";
      for (int k = 0; k < 3; ++k) {
        double e = (*ct->GetEnergyCutsVector(k))[j] / MeV;
        std::cerr << " " << e;
        if (std::abs(e - cutMeV) > 1e-5)
          throw std::runtime_error("Production-cut mismatch");
      }
      std::cerr << "\n";
    }
  if (!foundCuts)
    throw std::runtime_error("Material cut table missing");
  delete run;
}
using namespace ActsFatras;
using Charged = StandardChargedElectroMagneticInteractions;
using Neutral = InteractionList<PhotonConversion, ComptonScattering>;
struct Empty {};
template <class L>
using Actor = detail::SimulationActor<std::mt19937_64, Empty, L, Empty>;
// A planar cell is processed by the production actor; straight free flight
// selects the next cell. This intentionally retains the production slab
// approximation: conversion daughters get their sampled remaining column,
// emitted/scattered photons also retain sampled depth; other daughters leave
// the birth cell. Subdivision tests the remaining approximation.
struct Work {
  Particle particle;
  int cell;
  bool primary;
  std::optional<SlabPosition> birth;
};
double kinetic(const Particle& p) {
  return p.absoluteMomentum() *
         (p.absoluteMomentum() / (p.energy() + p.mass())) /
         Acts::UnitConstants::MeV;
}
void fatras() {
  auto* mat = G4NistManager::Instance()->FindOrBuildMaterial(cfg.material);
  auto material = Acts::Material::fromMassDensity(
      mat->GetRadlen() / mm, mat->GetNuclearInterLength() / mm,
      mat->GetA() / (g / mole), mat->GetZ(),
      mat->GetDensity() / (g / cm3) * Acts::UnitConstants::g /
          Acts::UnitConstants::cm3);
  material = Acts::Material::fromMolarDensity(
      material.X0(), material.L0(), material.Ar(), material.Z(),
      material.molarDensity(), material.molarElectronDensity(),
      mat->GetIonisation()->GetMeanExcitationEnergy() / MeV *
          Acts::UnitConstants::MeV);
  std::cerr << "MATERIAL " << cfg.material << " X0_mm " << material.X0()
            << " density_g_cm3 " << mat->GetDensity() / (g / cm3) << " I_eV "
            << material.meanExcitationEnergy() / Acts::UnitConstants::eV
            << "\n";
  const Acts::MaterialSlab slab(material, cfg.thickness / cfg.slices);
  std::mt19937_64 rng(cfg.seed);
  Actor<Charged> charged;
  Actor<Neutral> neutral;
  charged.generator = &rng;
  neutral.generator = &rng;
  charged.interactions = makeStandardChargedElectroMagneticInteractions(0.);
  auto& loss = charged.interactions.get<detail::StandardBetheBloch>().physics;
  loss.secondaryEnergyMin = cutMeV * Acts::UnitConstants::MeV;
  loss.bremsstrahlungPhotonMinEnergy = cutMeV * Acts::UnitConstants::MeV;
  charged.interactions.disable<detail::StandardBetheHeitler>();
  if (cfg.profile != "full")
    charged.interactions.disable<detail::StandardScattering>();
  for (int event = 0; event < cfg.n; ++event) {
    Particle p(Barcode().withParticle(1),
               static_cast<Acts::PdgParticle>(cfg.pdg));
    double e = cfg.energy * Acts::UnitConstants::MeV;
    p.setAbsoluteMomentum(std::sqrt(e * (e + 2 * p.mass())))
        .setDirection(0, 0, 1);
    std::vector<Work> queue{{p, 0, true, {}}};
    std::size_t processed = 0;
    unsigned steps = 0;
    while (processed < queue.size()) {
      if (queue.size() > 100000 || steps > 1000000)
        throw std::runtime_error("Cascade budget exceeded");
      auto work = queue[processed++];
      SingleParticleSimulationResult result;
      result.particle = work.particle;
      auto arm = [&] {
        if (result.particle.pdg() == Acts::eGamma)
          neutral.armPointLikeInteractions(result.particle, result);
        else
          charged.armPointLikeInteractions(result.particle, result);
      };
      arm();
      while (result.isAlive && result.particle.isAlive() &&
             result.particle.absoluteMomentum() > 0) {
        if (++steps > 1000000)
          throw std::runtime_error("Step budget exceeded");
        auto& track = result.particle;
        double ke = kinetic(track);
        if (track.pdg() == Acts::eGamma && ke < cutMeV)
          break;
        if (work.cell < 0 || work.cell >= cfg.slices) {
          escape(int(track.pdg()), ke, work.primary);
          break;
        }
        SlabPosition pos = work.birth.value_or(SlabPosition{
            slab, Acts::Vector3::UnitZ(), track.direction().z() > 0 ? 0. : 1.});
        work.birth.reset();
        auto column = pos.remaining(track.direction());
        result.generatedParticles.clear();
        result.generatedMaterial.clear();
        if (track.pdg() == Acts::eGamma)
          neutral.interact(column, result, &pos);
        else
          charged.interact(column, result, &pos);
        auto childMaterial = result.generatedMaterial.begin();
        for (std::size_t i = 0; i < result.generatedParticles.size(); ++i) {
          const auto child = result.generatedParticles[i];
          std::optional<SlabPosition> birthMaterial;
          if (childMaterial != result.generatedMaterial.end() && childMaterial->first == i) {
            birthMaterial = childMaterial->second;
            ++childMaterial;
          }
          const auto process = child.process();
          const bool continuation = child.pdg() == Acts::eGamma &&
                                    process == GenerationProcess::eOther;
          std::string name =
              process == GenerationProcess::eBremsstrahlung     ? "eBrem"
              : process == GenerationProcess::eIonisation       ? "eIoni"
              : process == GenerationProcess::ePhotonConversion ? "conv"
              : process == GenerationProcess::eOther            ? "compt"
                                                                : "?";
          if (!continuation)
            birth(int(child.pdg()), kinetic(child), name);
          if (cfg.mode == "primary" && !continuation)
            continue;
          if (child.pdg() == Acts::eGamma && kinetic(child) < cutMeV)
            continue;
          const int next = work.cell + (child.direction().z() > 0 ? 1 : -1);
          if (birthMaterial)
            queue.push_back({child, work.cell, continuation && work.primary,
                             birthMaterial});
          else
            queue.push_back({child, next, continuation && work.primary, {}});
        }
        work.cell += track.direction().z() > 0 ? 1 : -1;
      }
    }
    scores.finish();
  }
}
int main(int argc, char** argv) {
  if (argc != 12) {
    std::cerr << "backend material pdg energy_MeV thickness_mm n slices "
                 "profile mode seed output\n";
    return 2;
  }
  cfg = {argv[1],
         argv[2],
         argv[8],
         argv[9],
         argv[11],
         std::stoi(argv[3]),
         std::stoi(argv[6]),
         std::stoi(argv[7]),
         std::stod(argv[4]),
         std::stod(argv[5]),
         std::stol(argv[10])};
  if (cfg.backend == "g4")
    geant();
  else
    fatras();
  std::ofstream out(cfg.output);
  out << std::setprecision(12) << "metric,n,mean,sem\n";
  for (int k = 0; k < 11; ++k) {
    double mean = scores.sum[k] / scores.n;
    double var = std::max(
        0., (scores.sum2[k] - scores.n * mean * mean) / (scores.n - 1));
    out << names[k] << ',' << scores.n << ',' << mean << ','
        << std::sqrt(var / scores.n) << '\n';
  }
}
