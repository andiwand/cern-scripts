import argparse

p = argparse.ArgumentParser()
p.add_argument("--source", type=__import__("pathlib").Path, required=True)
p.add_argument("--work", type=__import__("pathlib").Path, required=True)
a = p.parse_args()
from pathlib import Path
import json, subprocess

w = a.work
s = a.source
t = (
    subprocess.check_output(
        [
            "git",
            "-C",
            str(s),
            "show",
            "cd100d7886:Fatras/include/ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp",
        ],
        text=True,
    )
    .replace("Ionisation", "ReferenceIonisation")
    .replace("eReferenceIonisation", "eIonisation")
)
(w / "ReferenceIonisation.hpp").write_text(t)
t = (
    subprocess.check_output(
        ["git", "-C", str(s), "show", "cd100d7886:Fatras/src/Physics/Ionisation.cpp"],
        text=True,
    )
    .replace(
        '"ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp"',
        '"ReferenceIonisation.hpp"',
    )
    .replace("Ionisation::", "ReferenceIonisation::")
)
(w / "ReferenceIonisation.cpp").write_text(t)
(w / "fast-stop-check.cpp").write_text(r"""
#include "ActsFatras/Physics/ElectroMagnetic/Ionisation.hpp"
#include "ReferenceIonisation.hpp"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"
#include <iostream>
#include <random>
int main(){using namespace Acts;using namespace ActsFatras;int cases=0,bad=0;
for(auto name:{"G4_C","G4_Si","G4_Cu","G4_Pb"}){
auto* mat=G4NistManager::Instance()->FindOrBuildMaterial(name);
auto native=Material::fromMassDensity(mat->GetRadlen()/mm,mat->GetNuclearInterLength()/mm,mat->GetA()/(g/mole),mat->GetZ(),mat->GetDensity()/(g/cm3)*UnitConstants::g/UnitConstants::cm3);
for(auto pdg:{eElectron,ePositron})for(int j=0;j<300;++j){
Particle p(Barcode().withParticle(1),pdg);double lo=1.01*native.meanExcitationEnergy(),hi=p.mass()*(std::sqrt(2.)-1);double ke=lo*std::pow(hi/lo,double(j)/299);p.setAbsoluteMomentum(std::sqrt(ke*(ke+2*p.mass())));
std::mt19937_64 gen(42);auto thin=p;ReferenceIonisation{1.}(gen,MaterialSlab(native,1e-8),thin);double loss=p.energy()-thin.energy();
for(double f:{1.,1.01,1.1,2.,10.}){auto old=p,now=p;std::mt19937_64 a(42),b(42);MaterialSlab slab(native,f*ke/loss*1e-8);ReferenceIonisation{1.}(a,slab,old);Ionisation{1.}(b,slab,now);++cases;if(old.absoluteMomentum()!=now.absoluteMomentum()||old.outcome()!=now.outcome()||a!=b){if(bad<12)std::cout<<name<<' '<<int(pdg)<<' '<<ke*1000<<' '<<f<<' '<<old.absoluteMomentum()<<' '<<now.absoluteMomentum()<<'\n';++bad;}}
}}
std::cout<<cases<<" cases; "<<bad<<" differences\n";return bad!=0;}
""")
c = json.loads((w / "stopping-build.json").read_text())
c = [str(w / "fast-stop-check.cpp") if x.endswith("/stopping.cpp") else x for x in c]
c[1:1] = [str(w / "ReferenceIonisation.cpp")]
c[c.index("-o") + 1] = str(w / "fast-stop-check")
(w / "fast-stop-check-build.json").write_text(json.dumps(c, indent=2))
subprocess.run(c, check=True)
subprocess.run([str(w / "fast-stop-check")], check=True)
