#include "Acts/Definitions/Units.hpp"
#include "Acts/EventData/BoundTrackParameters.hpp"
#include "Acts/Geometry/GeometryContext.hpp"
#include "Acts/MagneticField/ConstantBField.hpp"
#include "Acts/Material/HomogeneousVolumeMaterial.hpp"
#include "Acts/Material/Interactions.hpp"
#include "Acts/Propagator/SympyStepper.hpp"
#include "Acts/Propagator/detail/SympyBoundToFreeScaling.hpp"
#include "ActsTests/CommonHelpers/PredefinedMaterials.hpp"
#include "G4BetheBlochModel.hh"
#include "G4MuBetheBlochModel.hh"
#include "G4MuBremsstrahlungModel.hh"
#include "G4MuPairProductionModel.hh"
#include "G4MuonMinus.hh"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"
#include "FTFP_BERT.hh"
#include "G4RunManager.hh"
#include "G4EmCalculator.hh"
#include "G4VUserDetectorConstruction.hh"
#include "G4Box.hh"
#include "G4LogicalVolume.hh"
#include "G4PVPlacement.hh"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <functional>
using namespace Acts;
using namespace Acts::UnitLiterals;

class Detector : public G4VUserDetectorConstruction {
 public:
 G4VPhysicalVolume* Construct() override {
   auto* nist=G4NistManager::Instance();
   auto* world=new G4LogicalVolume(new G4Box("world",2000,2000,2000),nist->FindOrBuildMaterial("G4_Galactic"),"world");
   int i=0;
   for(auto name:{"G4_Fe","G4_lAr","G4_Si"}) {
     auto* lv=new G4LogicalVolume(new G4Box(name,10,10,10),nist->FindOrBuildMaterial(name),name);
     new G4PVPlacement(nullptr,G4ThreeVector(100*i++,0,0),lv,name,world,false,0);
   }
   return new G4PVPlacement(nullptr,{},world,"world",nullptr,false,0);
 }
};

double integrate(double p, double mass, double length, double h,
                 const std::function<double(double)>& stopping) {
  double e = std::hypot(p,mass);
  const int n = std::ceil(length/h); h=length/n;
  auto f=[&](double energy){return -stopping(std::sqrt(energy*energy-mass*mass));};
  for(int i=0;i<n;++i) {
    double a=f(e),b=f(e+h*a/2),c=f(e+h*b/2),d=f(e+h*c);
    e+=h*(a+2*b+2*c+d)/6;
  }
  return std::sqrt(e*e-mass*mass);
}

int main(int argc, char** argv) {
  std::string out=argc>1?argv[1]:".";
  const auto geo=GeometryContext::dangerouslyDefaultConstruct();
  const MagneticFieldContext mag;
  const auto particle=ParticleHypothesis::muon();
  const double mass=particle.mass();
  SympyStepper stepper(std::make_shared<ConstantBField>(Vector3::Zero()));
  auto run=[&](const Material& mat,double p,double length,double h,bool cov,bool gradient=true) {
    SympyStepper::Options opt(geo,mag);
    opt.initialStepSize=h; opt.maxStepSize=h; opt.stepTolerance=1e-6;
    opt.dense.includeGradient=gradient;
    auto state=stepper.makeState(opt);
    std::optional<BoundMatrix> covariance;
    if(cov) covariance=BoundMatrix::Identity()*1e-16;
    stepper.initialize(state,BoundTrackParameters::createCurvilinear(Vector4::Zero(),Vector3::UnitX(),-1/p,covariance,particle));
    HomogeneousVolumeMaterial volume(mat);
    while(state.pathAccumulated < length-1e-9) {
      if(state.nSteps>100000) throw std::runtime_error("Too many steps");
      state.stepSize.setUser(std::min(h,length-state.pathAccumulated));
      auto r=stepper.step(state,Direction::Forward(),&volume);
      if(!r.ok()) throw std::runtime_error(r.error().message());
    }
    return state;
  };
  std::ofstream numeric(out+"/numerics.csv"); numeric<<std::setprecision(14);
  numeric<<"material,p_GeV,length_mm,h_mm,p_out_GeV,reference_GeV,reference_halfstep_GeV,rejected,jac_qop,finite_diff_qop,path_derivative,expected_path_derivative,gradient_off_jac\n";
  for(auto [name,mat]:std::vector<std::pair<std::string,Material>>{{"Fe",ActsTests::makeIron()},{"LAr",ActsTests::makeLiquidArgon()},{"Si",ActsTests::makeSilicon()}}) {
    MaterialSlab slab(mat,1_mm);
    auto stop=[&](double p){return computeEnergyLossMean(slab,eMuon,mass,-1/p,1);};
    for(double p:{2.,10.,100.}) {
      double length=1000;
      double reference=integrate(p,mass,length,.02,stop);
      double reference2=integrate(p,mass,length,.01,stop);
      for(double h:{1000.,100.,10.,1.}) {
        auto st=run(mat,p,length,h,true);
        const double qp=-1/p,eps=std::abs(qp)*1e-3;
        auto plus=run(mat,-1/(qp+eps),length,h,false);
        auto minus=run(mat,-1/(qp-eps),length,h,false);
        double fd=(stepper.qOverP(plus)-stepper.qOverP(minus))/(2*eps);
        double qpf=stepper.qOverP(st),pf=stepper.absoluteMomentum(st);
        double expected=-std::hypot(pf,mass)/(pf*pf*pf)*stop(pf);
        auto nograd=run(mat,p,length,h,true,false);
        numeric<<name<<','<<p<<','<<length<<','<<h<<','<<pf<<','<<reference<<','<<reference2<<','<<st.statistics.nRejectedSteps<<','<<st.jacToGlobal(eFreeQOverP,eBoundQOverP)<<','<<fd<<','<<st.derivative[eFreeQOverP]<<','<<expected<<','<<nograd.jacToGlobal(eFreeQOverP,eBoundQOverP)<<'\n';
      }
    }
  }
  std::ofstream screen(out+"/current-screen.csv");screen<<std::setprecision(14);
  screen<<"material,thickness_mm,p_initial,p_final,e_loss,x_sigma,dir_sigma\n";
  for(auto [name,mat]:std::vector<std::pair<std::string,Material>>{{"fe",ActsTests::makeIron()},{"lar",ActsTests::makeLiquidArgon()}}) {
    for(double thickness:{10.,100.,1000.}) {
      for(int i=0;i<81;++i) {
        double p=2*std::pow(150.,i/80.);
        auto st=run(mat,p,thickness,1.,true);
        const double drift=1500-thickness/2;
        st.stepSize.setAccuracy(drift);st.stepSize.setUser(drift);
        auto res=stepper.step(st,Direction::Forward(),nullptr);
        if(!res.ok()) throw std::runtime_error(res.error().message());
        double pf=stepper.absoluteMomentum(st);
        stepper.transportToCurvilinear(st);
        auto cov=stepper.covariance(st).value();
        screen<<name<<','<<thickness<<','<<p<<','<<pf<<','<<std::hypot(p,mass)-std::hypot(pf,mass)<<','<<std::sqrt(cov(eBoundLoc0,eBoundLoc0))<<','<<std::sqrt(cov(eBoundTheta,eBoundTheta))<<'\n';
      }
    }
  }
  std::ofstream rates(out+"/rates.csv"); rates<<std::setprecision(14);
  rates<<"material,p_GeV,I_acts_eV,I_g4_eV,acts_ion_MeV_mm,acts_matched_I_MeV_mm,g4_ion_MeV_mm,g4_restricted_1MeV_MeV_mm,acts_rad_MeV_mm,g4_brems_MeV_mm,g4_pair_MeV_mm\n";
  G4RunManager manager;
  manager.SetUserInitialization(new Detector());
  manager.SetUserInitialization(new FTFP_BERT(0));
  manager.Initialize();
  manager.BeamOn(0);
  G4EmCalculator calculator;
  auto* mu=G4MuonMinus::Definition();
  for(auto [name,mat]:std::vector<std::pair<std::string,Material>>{{"Fe",ActsTests::makeIron()},{"lAr",ActsTests::makeLiquidArgon()},{"Si",ActsTests::makeSilicon()}}) {
    auto* g4=G4NistManager::Instance()->FindOrBuildMaterial("G4_"+name);
    double I=g4->GetIonisation()->GetMeanExcitationEnergy()/CLHEP::eV;
    auto matched=Material::fromMolarDensity(mat.X0(),mat.L0(),mat.Ar(),mat.Z(),mat.molarDensity(),mat.molarElectronDensity(),I*1_eV);
    for(double p:{.1,.3,1.,1.05,1.06,2.,3.,10.,100.,300.}) {
      double kinetic=(std::hypot(p,mass)-mass)/1_MeV;
      rates<<name<<','<<p<<','<<mat.meanExcitationEnergy()/1_eV<<','<<I<<','
        <<computeEnergyLossBethe(MaterialSlab(mat,1_mm),mass,-1/p,1)/1_MeV<<','
        <<computeEnergyLossBethe(MaterialSlab(matched,1_mm),mass,-1/p,1)/1_MeV<<','
        <<calculator.ComputeDEDX(kinetic,mu,"muIoni",g4,DBL_MAX)<<','
        <<calculator.ComputeDEDX(kinetic,mu,"muIoni",g4,1.)<<','
        <<computeEnergyLossRadiative(MaterialSlab(mat,1_mm),eMuon,mass,-1/p,1)/1_MeV<<','
        <<calculator.ComputeDEDX(kinetic,mu,"muBrems",g4,DBL_MAX)<<','
        <<calculator.ComputeDEDX(kinetic,mu,"muPairProd",g4,DBL_MAX)<<'\n';
    }
  }
}
