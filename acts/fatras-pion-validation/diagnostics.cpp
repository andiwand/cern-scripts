// External ODD pion diagnostics. No RNG draws and no changes to transport
// state.
#include "ActsExamples/Framework/WriterT.hpp"
#include "ActsExamples/Geant4/EventStore.hpp"
#include "ActsExamples/Geant4/Geant4Simulation.hpp"
#include "ActsExamples/Utilities/Paths.hpp"
#include "ActsFatras/Physics/Hadronic/NuclearInteractionTable.hpp"
#include <G4Event.hh>
#include <G4Material.hh>
#include <G4NistManager.hh>
#include <G4RunManager.hh>
#include <G4Step.hh>
#include <G4SystemOfUnits.hh>
#include <G4Track.hh>
#include <G4UserSteppingAction.hh>
#include <G4VProcess.hh>
#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <unordered_map>

namespace py = pybind11;
using namespace ActsExamples;
namespace {
void barcode(std::ostream &o, const SimBarcode &b) {
  for (auto x : b.asArray())
    o << x << ',';
}
const char *ids = "particle_id_pv,particle_id_sv,particle_id_part,particle_id_"
                  "gen,particle_id_subpart,";
struct PathRecord {
  SimBarcode id;
  int pdg = 0, inelastic = 0, elastic = 0;
  double p0 = 0, pt0 = 0, p = 0, l0 = 0, firstL0 = 0, hazard = 0,
         firstHazard = 0;
};
class Recorder : public G4UserSteppingAction {
  std::shared_ptr<Geant4::EventStore> store;
  std::string folder;
  std::vector<int> projectiles;
  std::string prefix;
  ActsFatras::NuclearInteractionTable table;
  int event = -1;
  std::ofstream interactions;
  std::unordered_map<int, PathRecord> paths;

public:
  Recorder(std::shared_ptr<Geant4::EventStore> s, std::string dir,
           const std::string &t, std::vector<int> pdgs, std::string stem)
      : store(std::move(s)), folder(std::move(dir)),
        projectiles(std::move(pdgs)), prefix(std::move(stem)), table([&] {
          std::ifstream f(t);
          return ActsFatras::NuclearInteractionTable::read(f);
        }()) {}
  void flush() {
    if (event < 0)
      return;
    interactions.flush();
    std::ofstream out(perEventFilepath(folder, prefix + "_paths.csv", event));
    out << std::setprecision(12) << ids
        << "pdg,p0,pt0,p_final,l0,first_l0,hazard,first_hazard,n_inelastic,n_"
           "elastic\n";
    for (const auto &[id, r] : paths) {
      barcode(out, r.id);
      out << r.pdg << ',' << r.p0 << ',' << r.pt0 << ',' << r.p << ',' << r.l0
          << ',' << r.firstL0 << ',' << r.hazard << ',' << r.firstHazard << ','
          << r.inelastic << ',' << r.elastic << '\n';
    }
  }
  void UserSteppingAction(const G4Step *step) override {
    const auto *track = step->GetTrack();
    const int pdg = track->GetDefinition()->GetPDGEncoding();
    const int now =
        G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
    if (now != event) {
      flush();
      interactions.close();
      paths.clear();
      event = now;
      interactions.open(
          perEventFilepath(folder, prefix + "_interactions.csv", event));
      interactions << std::setprecision(12) << ids
                   << "pdg,process,subtype,p,pt,dx,dy,dz,x,y,z,t_ns,material,"
                      "l0_material,l0_path,n_charged,n_accepted,n_photon,n_pi0,"
                      "leading_alive,leading_p,leading_pt\n";
    }
    if (std::find(projectiles.begin(), projectiles.end(), pdg) ==
        projectiles.end())
      return;
    auto it = store->trackIdMapping.find(track->GetTrackID());
    if (it == store->trackIdMapping.end())
      throw std::runtime_error("unregistered hadron");
    const auto *pre = step->GetPreStepPoint();
    const auto *post = step->GetPostStepPoint();
    const auto *mat = pre->GetMaterial();
    const auto *process = post->GetProcessDefinedStep();
    const double p = pre->GetMomentum().mag() / GeV;
    auto [rIt, inserted] = paths.try_emplace(track->GetTrackID());
    auto &r = rIt->second;
    if (inserted) {
      r.id = it->second;
      r.pdg = pdg;
      r.p0 = p;
      r.pt0 = pre->GetMomentum().perp() / GeV;
    }
    const double dl0 = step->GetStepLength() / mat->GetNuclearInterLength();
    const auto *channel =
        table.findReferenceChannel(static_cast<Acts::PdgParticle>(pdg));
    const double dh =
        channel ? dl0 * table.ratePerL0(*channel, p * Acts::UnitConstants::GeV)
                : 0;
    r.l0 += dl0;
    r.hazard += dh;
    r.p = post->GetMomentum().mag() / GeV;
    if (r.inelastic == 0) {
      r.firstL0 += dl0;
      r.firstHazard += dh;
    }
    if (!process || process->GetProcessType() != fHadronic)
      return;
    const int subtype = process->GetProcessSubType();
    if (subtype == 121)
      ++r.inelastic;
    if (subtype == 111)
      ++r.elastic;
    // Raw step-secondary counts include any along-step products. The analysis
    // uses truth creation processes and vertex matching for nuclear-only
    // yields.
    int charged = 0, accepted = 0, photon = 0, pi0 = 0;
    for (const auto *child : *step->GetSecondaryInCurrentStep()) {
      const auto *def = child->GetDefinition();
      if (std::abs(def->GetPDGEncoding()) >= 1000000000)
        continue;
      if (def->GetPDGCharge() != 0) {
        ++charged;
        if (child->GetMomentum().mag() / GeV >= .1 &&
            child->GetMomentum().perp() / GeV >= .05)
          ++accepted;
      }
      photon += def->GetPDGEncoding() == 22;
      pi0 += def->GetPDGEncoding() == 111;
    }
    const bool alive = track->GetTrackStatus() == fAlive ||
                       track->GetTrackStatus() == fStopButAlive;
    barcode(interactions, r.id);
    const auto d = pre->GetMomentumDirection();
    const auto x = post->GetPosition();
    interactions << pdg << ',' << process->GetProcessName() << ',' << subtype
                 << ',' << p << ',' << pre->GetMomentum().perp() / GeV << ','
                 << d.x() << ',' << d.y() << ',' << d.z() << ',' << x.x() / mm
                 << ',' << x.y() / mm << ',' << x.z() / mm << ','
                 << post->GetGlobalTime() / ns << ',' << mat->GetName() << ','
                 << mat->GetNuclearInterLength() / mm << ',' << r.l0 << ','
                 << charged << ',' << accepted << ',' << photon << ',' << pi0
                 << ',' << alive << ',' << r.p << ','
                 << post->GetMomentum().perp() / GeV << '\n';
  }
};
std::vector<std::weak_ptr<Recorder>> recorders;
class PionWriter : public WriterT<SimParticleContainer> {
  std::string folder;
  std::vector<int> projectiles;
  std::string prefix;

public:
  PionWriter(const std::string &input, const std::string &output,
             std::vector<int> pdgs, std::string stem)
      : WriterT(input, "HadronStateWriter", Acts::Logging::INFO),
        folder(output), projectiles(std::move(pdgs)), prefix(std::move(stem)) {}
  ProcessCode writeT(const AlgorithmContext &ctx,
                     const SimParticleContainer &particles) override {
    std::ofstream out(
        perEventFilepath(folder, prefix + "_states.csv", ctx.eventNumber));
    out << std::setprecision(12) << ids
        << "pdg,p0,pt0,px0,py0,pz0,p_final,pt_final,dx,dy,dz,x,y,z,t_ns,l0,"
           "outcome\n";
    for (const auto &particle : particles) {
      if (std::find(projectiles.begin(), projectiles.end(), particle.pdg()) ==
          projectiles.end())
        continue;
      const auto &f = particle.finalState();
      auto p = particle.momentum();
      auto d = f.direction();
      barcode(out, particle.particleId());
      out << particle.pdg() << ',' << particle.absoluteMomentum() << ','
          << p.head<2>().norm() << ',' << p.x() << ',' << p.y() << ',' << p.z()
          << ',' << f.absoluteMomentum() << ',' << f.momentum().head<2>().norm()
          << ',' << d.x() << ',' << d.y() << ',' << d.z() << ','
          << f.position().x() << ',' << f.position().y() << ','
          << f.position().z() << ',' << f.time() / Acts::UnitConstants::ns
          << ',' << f.pathInL0() << ',' << static_cast<int>(f.outcome())
          << '\n';
    }
    return ProcessCode::SUCCESS;
  }
};
} // namespace
PYBIND11_MODULE(pion_diagnostics, mod) {
  mod.def(
      "make_geant4",
      [](Geant4Simulation::Config cfg, const std::string &dir,
         const std::string &table, Acts::Logging::Level level,
         std::vector<int> pdgs, std::string prefix) {
        cfg.steppingActionFactory =
            [dir, table, pdgs,
             prefix](std::shared_ptr<Geant4::EventStore> store) {
              auto r = std::make_shared<Recorder>(std::move(store), dir, table,
                                                  pdgs, prefix);
              recorders.push_back(r);
              return r;
            };
        return std::make_shared<Geant4Simulation>(
            cfg, Acts::getDefaultLogger("Geant4Simulation", level));
      },
      py::arg("config"), py::arg("output"), py::arg("table"), py::arg("level"),
      py::arg("projectiles") = std::vector<int>{211, -211},
      py::arg("prefix") = "pion");
  py::class_<PionWriter, IWriter, std::shared_ptr<PionWriter>>(mod,
                                                               "PionWriter")
      .def(py::init<const std::string &, const std::string &, std::vector<int>,
                    std::string>(),
           py::arg("input"), py::arg("output"),
           py::arg("projectiles") = std::vector<int>{211, -211},
           py::arg("prefix") = "pion");
  mod.def("beryllium", [] {
    auto *material = G4NistManager::Instance()->FindOrBuildMaterial("G4_Be");
    py::dict out;
    out["x0"] = material->GetRadlen() / CLHEP::mm;
    out["l0"] = material->GetNuclearInterLength() / CLHEP::mm;
    out["A"] = material->GetA() / (CLHEP::g / CLHEP::mole);
    out["Z"] = material->GetZ();
    out["rho"] = material->GetDensity() / (CLHEP::g / CLHEP::cm3) *
                 Acts::UnitConstants::g / std::pow(Acts::UnitConstants::cm, 3);
    out["density_g_cm3"] = material->GetDensity() / (CLHEP::g / CLHEP::cm3);
    return out;
  });
  mod.def("flush", [] {
    for (auto &w : recorders)
      if (auto r = w.lock())
        r->flush();
  });
}
