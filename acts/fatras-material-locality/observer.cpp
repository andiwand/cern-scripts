// Observational G4 wrappers: delegate every callback; never alter tracks/RNG.
#include <G4RunManager.hh>
#include <G4UserSteppingAction.hh>
#include <G4UserTrackingAction.hh>
#include <G4Step.hh>
#include <G4Track.hh>
#include <G4VProcess.hh>
#include <G4Event.hh>
#include <G4Run.hh>
#include <G4VPhysicalVolume.hh>
#include <G4ProductionCutsTable.hh>
#include <G4MaterialCutsCouple.hh>
#include <G4Material.hh>
#include <G4SystemOfUnits.hh>
#include <fstream>
#include <iomanip>
#include <memory>
#include <unordered_map>
#include <pybind11/pybind11.h>
namespace {
struct Birth { int pdg; std::string process, material, volume; double ke; G4ThreeVector pos; };
std::unordered_map<int,Birth> births;
std::ofstream output;
int currentEvent=-1;
std::string outputPath;
void dumpCuts(){
  std::ofstream cuts(outputPath+".cuts.tsv");
  cuts<<std::setprecision(12)<<"material\tdensity_g_cm3\telectron_cut_MeV\tphoton_cut_MeV\n";
  auto* table=G4ProductionCutsTable::GetProductionCutsTable();
  for(std::size_t i=0;i<table->GetTableSize();++i){
   auto* material=table->GetMaterialCutsCouple(i)->GetMaterial();
   cuts<<material->GetName()<<'\t'<<material->GetDensity()/(g/cm3)<<'\t'<<(*table->GetEnergyCutsVector(1))[i]/MeV<<'\t'<<(*table->GetEnergyCutsVector(0))[i]/MeV<<'\n';
  }
}
struct Tracking final : G4UserTrackingAction {
  std::unique_ptr<G4UserTrackingAction> original;
  explicit Tracking(G4UserTrackingAction* action):original(action){}
  void PreUserTrackingAction(const G4Track* t) override {
    original->PreUserTrackingAction(t);
    int ev=G4RunManager::GetRunManager()->GetCurrentRun()->GetRunID();
    if(currentEvent<0)dumpCuts();
    if(ev!=currentEvent){births.clear();currentEvent=ev;}
    auto* p=t->GetCreatorProcess();
    births[t->GetTrackID()]={t->GetDefinition()->GetPDGEncoding(),p?std::string(p->GetProcessName()):"primary","unknown","unknown",t->GetKineticEnergy()/MeV,t->GetPosition()};
  }
  void PostUserTrackingAction(const G4Track* t) override {original->PostUserTrackingAction(t);}
};
struct Stepping final : G4UserSteppingAction {
  std::unique_ptr<G4UserSteppingAction> original;
  explicit Stepping(G4UserSteppingAction* action):original(action){}
  void UserSteppingAction(const G4Step* s) override {
    // Read before forwarding: the original action may change track status.
    const auto* t=s->GetTrack();const auto* v=t->GetVolume();
    bool sensitive=v && v->GetName().find("ActsSensitive#")!=std::string::npos;
    const auto* pre=s->GetPreStepPoint();const auto* post=s->GetPostStepPoint();
    auto& birth=births.at(t->GetTrackID());
    if(t->GetCurrentStepNumber()==1){birth.material=pre->GetMaterial()->GetName();birth.volume=pre->GetPhysicalVolume()->GetName();}
    const auto* end=post->GetProcessDefinedStep();
    bool boundary=post->GetStepStatus()==fGeomBoundary || post->GetStepStatus()==fWorldBoundary;
    bool stopped=post->GetKineticEnergy()==0;
    bool decayed=end && end->GetProcessType()==fDecay;
    if(sensitive && t->GetDefinition()->GetPDGCharge()!=0 && (boundary||stopped||decayed)){
      const auto& b=births.at(t->GetTrackID());
      auto parent=births.find(t->GetParentID());
      const auto x=post->GetPosition();
      output<<currentEvent<<'\t'<<t->GetTrackID()<<'\t'<<t->GetParentID()<<'\t'<<b.pdg<<'\t'<<b.process<<'\t'<<b.material<<'\t'<<b.volume<<'\t'<<b.ke<<'\t'<<b.pos.x()/mm<<'\t'<<b.pos.y()/mm<<'\t'<<b.pos.z()/mm<<'\t'<<v->GetName()<<'\t'<<x.x()/mm<<'\t'<<x.y()/mm<<'\t'<<x.z()/mm<<'\t'<<post->GetGlobalTime()/ns<<'\t'<<stopped<<'\t'<<(parent!=births.end()?parent->second.process:"unknown")<<'\t'<<(parent!=births.end()?parent->second.ke:-1)<<'\n';
    }
    original->UserSteppingAction(s);
  }
};
}
PYBIND11_MODULE(gap_observer,module){
 module.def("install",[](const std::string& path){
  if(output.is_open())throw std::runtime_error("observer already installed");
  outputPath=path;output.open(path);if(!output)throw std::runtime_error("cannot open observer output");
  output<<std::setprecision(12)<<"event\ttrack\tparent\tpdg\tcreator\tbirth_material\tbirth_volume\tbirth_ke_MeV\tbx\tby\tbz\thit_volume\tx\ty\tz\tt_ns\tstopped\tparent_creator\tparent_birth_ke_MeV\n";
  auto* r=G4RunManager::GetRunManager();
  auto* tr=const_cast<G4UserTrackingAction*>(r->GetUserTrackingAction());
  auto* st=const_cast<G4UserSteppingAction*>(r->GetUserSteppingAction());
  if(!tr||!st)throw std::runtime_error("missing original G4 actions");
  r->SetUserAction(new Tracking(tr));r->SetUserAction(new Stepping(st));

 });
 module.def("flush",[]{output.flush();});
}
