#include "ActsFatras/Physics/Hadronic/NuclearInteractionTable.hpp"
#include <fstream>
#include <iostream>
#include <cmath>
#include <string>
int main(int argc,char**argv) {
 try {
  if(argc!=2 && !(argc==3 && std::string(argv[2])=="--load-only"))return 2;
  std::ifstream in(argv[1]);auto table=ActsFatras::NuclearInteractionTable::read(in);
  if(argc==3){std::cout<<"{\"channels\":"<<table.channels().size()<<"}\n";return 0;}
  std::size_t n=0;double maximum=0;
  for(const auto& channel:table.channels()) for(std::size_t b=0;b<channel.bins.size();++b) {
   const auto& bin=channel.bins[b];
   const double middle=b+1<channel.bins.size()?std::sqrt(bin.momentum*channel.bins[b+1].momentum):bin.momentum;
   for(const auto& event:bin.events)for(double p:{bin.momentum,middle}) {
    auto particle=ActsFatras::Particle(ActsFatras::Barcode().withParticle(1),channel.pdg).setAbsoluteMomentum(p).setDirection(1,2,3);
    auto sample=table.sample(event,particle,0.3);
    auto sum=sample.remnant;
    for(const auto& product:sample.products){sum.head<3>()+=product.momentum;sum[3]+=std::hypot(product.mass,product.momentum.norm());}
    auto expected=particle.fourMomentum();expected[3]+=event.targetMass;
    double delta=(sum-expected).norm()/expected.norm();maximum=std::max(maximum,delta);++n;
    if(delta>1e-6)throw std::runtime_error("four-momentum mismatch");
   }
  }
  std::cout<<"{\"samples_checked\":"<<n<<",\"max_relative_closure\":"<<maximum<<"}\n";
 } catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}
}
