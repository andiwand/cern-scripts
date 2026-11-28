#include "FTFP_BERT.hh"
#include "G4Box.hh"
#include "G4EmParameters.hh"
#include "G4Event.hh"
#include "G4LogicalVolume.hh"
#include "G4MuonMinus.hh"
#include "G4NistManager.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleGun.hh"
#include "G4ProcessManager.hh"
#include "G4ProductionCutsTable.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepLimiterPhysics.hh"
#include "G4SystemOfUnits.hh"
#include "G4UserEventAction.hh"
#include "G4UserLimits.hh"
#include "G4UserStackingAction.hh"
#include "G4UserSteppingAction.hh"
#include "G4VMultipleScattering.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "Randomize.hh"
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

struct Config {
  std::string material, mode, out;
  double p, length, step, cut;
  int events, seed;
};
struct Record {
  // status, exit y,z, direction y,z, exit p, screen y,z, direction y,z,
  // material path, screen p. Geant4 units: mm and MeV.
  std::array<double, 12> values;
  void reset() {
    values.fill(std::numeric_limits<double>::quiet_NaN());
    values[0] = 0;
    values[10] = 0;
  }
};
class Detector : public G4VUserDetectorConstruction {
  Config cfg;

public:
  explicit Detector(Config c) : cfg(c) {}
  G4VPhysicalVolume *Construct() override {
    auto *nist = G4NistManager::Instance();
    auto *vacuum = nist->FindOrBuildMaterial("G4_Galactic");
    auto *world = new G4LogicalVolume(new G4Box("world", 2000, 1000, 1000),
                                      vacuum, "world");
    auto *mat = nist->FindOrBuildMaterial("G4_" + cfg.material);
    auto *slab = new G4LogicalVolume(
        new G4Box("slab", cfg.length / 2, cfg.length / 2, cfg.length / 2), mat,
        "slab");
    slab->SetUserLimits(new G4UserLimits(cfg.step));
    new G4PVPlacement(nullptr, {}, slab, "slab", world, false, 0);
    auto *screen = new G4LogicalVolume(new G4Box("screen", .0005, 500, 500),
                                       vacuum, "screen");
    new G4PVPlacement(nullptr, {1500.0005, 0, 0}, screen, "screen", world,
                      false, 0);
    std::ofstream meta(cfg.out + ".material");
    meta << std::setprecision(15) << "X0_mm " << mat->GetRadlen() << "\nI_eV "
         << mat->GetIonisation()->GetMeanExcitationEnergy() / eV
         << "\ndensity_g_cm3 " << mat->GetDensity() / (g / cm3) << '\n';
    return new G4PVPlacement(nullptr, {}, world, "world", nullptr, false, 0);
  }
};
class Gun : public G4VUserPrimaryGeneratorAction {
  G4ParticleGun gun{1};

public:
  explicit Gun(const Config &c) {
    gun.SetParticleDefinition(G4MuonMinus::Definition());
    gun.SetParticleMomentum(c.p * GeV);
    gun.SetParticlePosition({-1500, 0, 0});
    gun.SetParticleMomentumDirection({1, 0, 0});
  }
  void GeneratePrimaries(G4Event *e) override { gun.GeneratePrimaryVertex(e); }
};
class Event : public G4UserEventAction {
  Record &record;
  std::ofstream &output;

public:
  Event(Record &r, std::ofstream &o) : record(r), output(o) {}
  void BeginOfEventAction(const G4Event *) override { record.reset(); }
  void EndOfEventAction(const G4Event *) override {
    output.write(reinterpret_cast<const char *>(record.values.data()),
                 sizeof(record.values));
  }
};
class Stack : public G4UserStackingAction {
  G4ClassificationOfNewTrack ClassifyNewTrack(const G4Track *t) override {
    return t->GetParentID() == 0 ? fUrgent : fKill;
  }
};
class Steps : public G4UserSteppingAction {
  Record &record;
  double length;

public:
  Steps(Record &r, double l) : record(r), length(l) {}
  void UserSteppingAction(const G4Step *step) override {
    if (step->GetTrack()->GetParentID() != 0)
      return;
    auto *pre = step->GetPreStepPoint();
    auto *post = step->GetPostStepPoint();
    const auto name = pre->GetPhysicalVolume()->GetName();
    auto &v = record.values;
    if (name == "slab") {
      v[10] += step->GetStepLength();
      if (post->GetStepStatus() == fGeomBoundary &&
          post->GetPosition().x() >= length / 2 - 1e-6) {
        v[0] = 1;
        v[1] = post->GetPosition().y();
        v[2] = post->GetPosition().z();
        v[3] = post->GetMomentumDirection().y();
        v[4] = post->GetMomentumDirection().z();
        v[5] = post->GetMomentum().mag();
      }
    }
    if (name == "screen") {
      v[0] = 2;
      v[6] = pre->GetPosition().y();
      v[7] = pre->GetPosition().z();
      v[8] = pre->GetMomentumDirection().y();
      v[9] = pre->GetMomentumDirection().z();
      v[11] = pre->GetMomentum().mag();
      step->GetTrack()->SetTrackStatus(fStopAndKill);
    }
  }
};
int main(int argc, char **argv) {
  if (argc != 10) {
    std::cerr << "material p_GeV length_mm maxstep_mm mode events seed cut_mm "
                 "output\n";
    return 1;
  }
  Config cfg{argv[1],
             argv[5],
             argv[9],
             std::stod(argv[2]),
             std::stod(argv[3]),
             std::stod(argv[4]),
             std::stod(argv[8]),
             std::stoi(argv[6]),
             std::stoi(argv[7])};
  CLHEP::HepRandom::setTheSeed(cfg.seed);
  Record record;
  std::ofstream output(cfg.out, std::ios::binary);
  G4RunManager run;
  run.SetUserInitialization(new Detector(cfg));
  auto *physics = new FTFP_BERT(0);
  physics->RegisterPhysics(new G4StepLimiterPhysics());
  physics->SetDefaultCutValue(cfg.cut * mm);
  run.SetUserInitialization(physics);
  if (cfg.mode == "ioncsda" ||
      (cfg.mode == "constant_uncut" || cfg.mode == "constant_all")) {
    G4EmParameters::Instance()->SetLossFluctuations(false);
    G4ProductionCutsTable::GetProductionCutsTable()->SetEnergyRange(100 * eV,
                                                                    1e9 * GeV);
    if (cfg.mode == "constant_all")
      G4ProductionCutsTable::GetProductionCutsTable()->SetMaxEnergyCut(1e9 *
                                                                       GeV);
  }
  run.SetUserAction(new Gun(cfg));
  run.SetUserAction(new Event(record, output));
  run.SetUserAction(new Steps(record, cfg.length));
  run.SetUserAction(new Stack());
  run.Initialize();
  run.BeamOn(0);
  if (cfg.mode == "constant_all") {
    auto *cuts = G4ProductionCutsTable::GetProductionCutsTable();
    cuts->SetEnergyCutVector(
        std::vector<double>(cuts->GetTableSize(), 1e6 * GeV), 1);
    cuts->UpdateCoupleTable(nullptr);
    run.PhysicsHasBeenModified();
  }
  run.BeamOn(0);
  auto *table = G4ProductionCutsTable::GetProductionCutsTable();
  for (std::size_t i = 0; i < table->GetTableSize(); ++i) {
    std::cout << "ELECTRON_CUT_MeV "
              << table->GetMaterialCutsCouple(i)->GetMaterial()->GetName()
              << " " << (*table->GetEnergyCutsVector(1))[i] << '\n';
  }

  auto *pm = G4MuonMinus::Definition()->GetProcessManager();
  for (int i = 0; i < pm->GetProcessListLength(); ++i) {
    auto *process = (*pm->GetProcessList())[i];
    auto name = process->GetProcessName();
    bool active = true;
    bool transport = name == "Transportation" || name == "StepLimiter";
    bool scattering = name == "muMsc" || name == "msc" || name == "CoulombScat";
    if (cfg.mode == "constant" ||
        (cfg.mode == "constant_uncut" || cfg.mode == "constant_all"))
      active = transport || scattering;
    if (cfg.mode == "msc")
      active = transport || name == "muMsc" || name == "msc";
    if (cfg.mode == "ion" || cfg.mode == "ioncsda")
      active = transport || scattering || name == "muIoni";
    if (cfg.mode == "no_scatter")
      active = !scattering;
    pm->SetProcessActivation(process, active);
    std::cout << "PROCESS " << name << " " << active;
    if (auto *msc = dynamic_cast<G4VMultipleScattering *>(process))
      std::cout << " MODEL " << msc->EmModel()->GetName();
    std::cout << '\n';
  }
  std::cout << "FLUCTUATIONS " << G4EmParameters::Instance()->LossFluctuation()
            << '\n';
  run.BeamOn(cfg.events);
}
