#include "NNInferenceStudy.h"
#include <algorithm>
#include <array>
#include <chrono>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

using Input=std::array<float,67>;
using Clock=std::chrono::steady_clock;
std::vector<Input> readInputs(const std::string& path,std::size_t limit) {
  std::ifstream f(path,std::ios::binary|std::ios::ate);
  if(!f) throw std::runtime_error("Cannot open inputs");
  auto bytes=f.tellg();
  if(bytes%sizeof(Input)) throw std::runtime_error("Invalid input file size");
  std::size_t count=bytes/sizeof(Input);
  std::vector<Input> all(count);f.seekg(0);f.read(reinterpret_cast<char*>(all.data()),bytes);
  if(!f || !count) throw std::runtime_error("Empty/truncated inputs");
  std::vector<Input> result;
  limit=std::min(limit,count);
  for(std::size_t i=0;i<limit;++i) result.push_back(all[i*count/limit]);
  return result;
}
int main(int argc,char** argv) try {
  if(argc<2) throw std::runtime_error("Expected generate|dump|time");
  const std::string mode=argv[1];
  if(mode=="generate") {
    std::ofstream out(argv[2],std::ios::binary);
    std::mt19937 rng(44521);
    std::uniform_real_distribution<float> charge(0,50000),angle(-1.4,1.4);
    for(unsigned j=0;j<2000;++j) {
      Input x{};
      for(unsigned k=0;k<49;++k) x[k]=(rng()%8==0) ? charge(rng) : 0;
      for(unsigned k=49;k<63;++k) x[k]=0.05;
      x[63]=rng()%5;x[64]=rng()%2 ? 0 : 2;x[65]=angle(rng);x[66]=angle(rng);
      out.write(reinterpret_cast<char*>(x.data()),sizeof(x));
    }
    return out ? 0 : 1;
  }
  if(argc<6) throw std::runtime_error("Expected mode backend inputs output/count count/repeats [pressure_bytes]");
  const std::string backend=argv[2];
  const char* modelDir=std::getenv("NN_STUDY_MODEL_DIR");
  if(!modelDir) throw std::runtime_error("NN_STUDY_MODEL_DIR missing");
  std::size_t count=std::stoul(mode=="dump" ? argv[5] : argv[4]);
  auto input=readInputs(argv[3],count);
  nnstudy::Engine engine(backend,modelDir);
  if(mode=="dump") {
    std::ofstream out(argv[4],std::ios::binary);
    std::feclearexcept(FE_ALL_EXCEPT);
    for(const auto& x:input) {
      std::array<float,33> y{};
      unsigned offset=0;
      for(unsigned m=0;m<4;++m) { engine.infer(m,x.data(),y.data()+offset);offset+=m==0 ? 3 : 5*m; }
      out.write(reinterpret_cast<char*>(y.data()),sizeof(y));
    }
    const int exceptions=std::fetestexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW);
    if(exceptions) throw std::runtime_error("Floating-point exception flags: "+std::to_string(exceptions));
    std::cout<<"Dumped "<<input.size()<<" inputs, all four networks, "<<backend<<'\n';
    return out ? 0 : 1;
  }
  if(mode!="time") throw std::runtime_error("Invalid mode");
  unsigned repeats=std::stoul(argv[5]);
  std::size_t pressureBytes=argc>6 ? std::stoul(argv[6]) : 0;
  std::vector<float> pressure(pressureBytes/sizeof(float),1.f);
  double checksum=0; volatile float pressureSink=0;
  auto one=[&](const Input& x) {
    std::array<float,3> p;std::array<float,15> pos;
    engine.infer(0,x.data(),p.data());
    unsigned n=std::max_element(p.begin(),p.end())-p.begin()+1;
    engine.infer(n,x.data(),pos.data());
    checksum+=p[0]+pos[1]+pos[3]+n;
  };
  for(unsigned i=0;i<1000;++i) one(input[i%input.size()]);
  std::cout<<std::setprecision(12)<<"{\"backend\":\""<<backend<<"\",\"samples\":"<<input.size()<<",\"pressure_bytes\":"<<pressureBytes<<",\"cycle_us\":[";
  for(unsigned r=0;r<repeats;++r) {
    double seconds=0;
    if(pressure.empty()) {
      const auto begin=Clock::now();
      for(const auto& x:input) one(x);
      seconds=std::chrono::duration<double>(Clock::now()-begin).count();
    } else {
      for(const auto& x:input) {
        float sum=0;
        for(std::size_t k=0;k<pressure.size();k+=16) sum+=pressure[k];
        pressureSink=sum;
        const auto begin=Clock::now();one(x);
        seconds+=std::chrono::duration<double>(Clock::now()-begin).count();
      }
    }
    if(r) std::cout<<',';
    std::cout<<seconds*1e6/input.size()<<std::flush;
  }
  std::cout<<"],\"checksum\":"<<checksum<<",\"pressure_checksum\":"<<pressureSink<<"}\n";
  return 0;
} catch(const std::exception& e) { std::cerr<<e.what()<<'\n';return 1; }
