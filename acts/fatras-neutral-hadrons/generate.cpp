// Offline Geant4 interaction-library generator. No ACTS runtime dependency.
#include "G4Box.hh"
#include "G4CrossSectionDataStore.hh"
#include "G4DynamicParticle.hh"
#include "G4HadronicProcess.hh"
#include "G4HadronicProcessType.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"
#include "G4NistManager.hh"
#include "G4NucleiProperties.hh"
#include "G4Nucleus.hh"
#include "G4PVPlacement.hh"
#include "G4ParticleChange.hh"
#include "G4ParticleTable.hh"
#include "G4ProcessManager.hh"
#include "G4RunManager.hh"
#include "G4Step.hh"
#include "G4StepPoint.hh"
#include "G4SystemOfUnits.hh"
#include "G4Track.hh"
#include "G4VUserDetectorConstruction.hh"
#include "FTFP_BERT.hh"
#include "Randomize.hh"
#include "CLHEP/Vector/LorentzVector.h"
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

struct Detector : G4VUserDetectorConstruction {
  G4Material* material;
  G4LogicalVolume* logical = nullptr;
  explicit Detector(G4Material* m) : material(m) {}
  G4VPhysicalVolume* Construct() override {
    logical = new G4LogicalVolume(new G4Box("world", 1*m, 1*m, 1*m), material, "world");
    return new G4PVPlacement(nullptr, {}, logical, "world", nullptr, false, 0);
  }
};
struct Product { int pdg; double mass, charge; CLHEP::HepLorentzVector p; };
struct Event { double targetMass, residualMass, residualCharge; G4ThreeVector residual;
               std::vector<Product> products; };

int main(int argc, char** argv) {
  if (argc < 7) {
    std::cerr << "usage: generate-table OUTPUT MATERIAL EVENTS SEED PDG_LIST P_GEV...\n";
    return 2;
  }
  try {
    const int count = std::stoi(argv[3]);
    if (count <= 0) throw std::runtime_error("EVENTS must be positive");
    std::vector<double> momenta;
    for (int i=6; i<argc; ++i) {
      double p=std::stod(argv[i])*GeV;
      if (!(p>0) || (!momenta.empty() && p<=momenta.back()))
        throw std::runtime_error("momenta must be positive and increasing");
      momenta.push_back(p);
    }
    if (momenta.size()<2) throw std::runtime_error("at least two momentum nodes required");
    std::vector<int> projectiles;
    std::istringstream pdgs(argv[5]); std::string token;
    while (std::getline(pdgs,token,',')) {
      int pdg=std::stoi(token);
      if (pdg!=211 && pdg!=-211 && pdg!=2212 && pdg!=2112 && pdg!=130)
        throw std::runtime_error("unsupported projectile");
      projectiles.push_back(pdg);
    }
    if (projectiles.empty()) throw std::runtime_error("no projectiles");
    G4Random::setTheSeed(std::stol(argv[4]));
    auto* material=G4NistManager::Instance()->FindOrBuildMaterial(argv[2]);
    if (!material || material->GetNumberOfElements()!=1)
      throw std::runtime_error("first generator supports elemental materials only");
    auto run=std::make_unique<G4RunManager>();
    auto* detector=new Detector(material);
    run->SetUserInitialization(detector);
    auto* physics=new FTFP_BERT(0);
    run->SetUserInitialization(physics);
    run->Initialize();
    // Initialize physics tables without shooting a transport event.
    run->BeamOn(0);
    std::ostringstream output;
    output << std::setprecision(17) << "ACTS_FATRAS_NUCLEAR_V1\n" << projectiles.size() << "\n";
    unsigned int nullCollisions=0;
    for (int pdg : projectiles) {
      auto* definition=G4ParticleTable::GetParticleTable()->FindParticle(pdg);
      G4HadronicProcess* process=nullptr;
      auto* processes=definition->GetProcessManager()->GetProcessList();
      for (int i=0; i<processes->size(); ++i) {
        auto* candidate=(*processes)[i];
        if (candidate->GetProcessSubType()==fHadronInelastic)
          process=dynamic_cast<G4HadronicProcess*>(candidate);
      }
      if (!process) throw std::runtime_error("missing inelastic process");
      const double mass=definition->GetPDGMass();
      const auto* element=(*material->GetElementVector())[0];
      output << pdg << ' ' << mass/GeV << ' ' << element->GetA()/(g/mole)
             << ' ' << element->GetZ() << ' ' << momenta.size() << '\n';
      for (double momentum : momenta) {
        double kinetic=std::hypot(momentum,mass)-mass;
        G4DynamicParticle probe(definition,{0,0,1},kinetic);
        // macroscopic cross section (inverse length), made dimensionless by L0.
        double rate=process->GetCrossSectionDataStore()->ComputeCrossSection(&probe,material)
                    * material->GetNuclearInterLength();
        std::vector<Event> events;
        if (rate>0) for (int attempt=0; events.size()<static_cast<unsigned>(count); ++attempt) {
          if (attempt>100*count) throw std::runtime_error("too many null interactions");
          G4Track track(new G4DynamicParticle(definition,{0,0,1},kinetic),0,{});
          G4Step step;
          step.SetTrack(&track);
          track.SetStep(&step);
          step.GetPreStepPoint()->SetMaterial(material);
          step.GetPreStepPoint()->SetMaterialCutsCouple(detector->logical->GetMaterialCutsCouple());
          step.GetPostStepPoint()->SetMaterial(material);
          process->StartTracking(&track);
          // GetMeanFreePath initialises the internal projectile/material cache.
          G4ForceCondition condition=NotForced;
          process->GetMeanFreePath(track,0,&condition);
          auto* change=dynamic_cast<G4ParticleChange*>(process->PostStepDoIt(track,step));
          if (!change) throw std::runtime_error("unexpected particle-change type");
          auto* nucleus=process->GetTargetNucleus();
          const double target=G4NucleiProperties::GetNuclearMass(nucleus->GetA_asInt(),nucleus->GetZ_asInt());
          CLHEP::HepLorentzVector initial(0,0,momentum,std::hypot(momentum,mass)+target);
          CLHEP::HepLorentzVector residual=initial;
          double residualCharge=element->GetZ()+definition->GetPDGCharge()/eplus;
          std::vector<Product> products;
          const auto add=[&](const G4DynamicParticle& particle) {
            // Fold nuclear fragments into the untransported residual system.
            if (std::abs(particle.GetPDGcode())>=1000000000) return;
            auto p=particle.Get4Momentum();
            products.push_back({particle.GetPDGcode(),particle.GetMass(),particle.GetCharge()/eplus,p});
            residual-=p;
            residualCharge-=particle.GetCharge()/eplus;
          };
          if (change->GetTrackStatus()==fAlive || change->GetTrackStatus()==fStopButAlive) {
            G4DynamicParticle leading(definition,*change->GetMomentumDirection(),change->GetEnergy());
            add(leading);
          }
          const int secondaries=change->GetNumberOfSecondaries();
          for (int i=0;i<secondaries;++i) {
            auto* secondary=change->GetSecondary(i);
            add(*secondary->GetDynamicParticle());
            delete secondary;
          }
          change->Clear();
          // Null collisions are not inelastic events; retry and record their count.
          if (secondaries==0 && products.size()==1 &&
              (products[0].p.vect()-G4ThreeVector(0,0,momentum)).mag()<1e-8*MeV &&
              std::abs(products[0].p.e()-std::hypot(momentum,mass))<1e-8*MeV) {
            ++nullCollisions; continue;
          }
          if (!(residual.e()>0 && residual.m2()>=0))
            throw std::runtime_error("spacelike residual: cannot write conserving event");
          const auto boost=-initial.boostVector();
          residual.boost(boost);
          for (auto& product:products) product.p.boost(boost);
          events.push_back({target,residual.m(),residualCharge,residual.vect(),std::move(products)});
        }
        output << momentum/GeV << ' ' << rate << ' ' << events.size() << '\n';
        for (const auto& event:events) {
          output << event.targetMass/GeV << ' ' << event.residualMass/GeV << ' ' << event.residualCharge
                 << ' ' << event.residual.x()/GeV << ' ' << event.residual.y()/GeV << ' ' << event.residual.z()/GeV
                 << ' ' << event.products.size() << '\n';
          for (const auto& product:event.products)
            output << product.pdg << ' ' << product.mass/GeV << ' ' << product.charge
                   << ' ' << product.p.px()/GeV << ' ' << product.p.py()/GeV << ' ' << product.p.pz()/GeV << '\n';
        }
        std::cerr << "pdg=" << pdg << " p=" << momentum/GeV << " rate/L0=" << rate << " events=" << events.size() << '\n';
      }
    }
    std::ofstream file(argv[1]);
    if (!file) throw std::runtime_error("cannot create output");
    file << output.str();
    if (!file) throw std::runtime_error("failed writing output");
    std::cerr << "null_collisions=" << nullCollisions << '\n';
  } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
