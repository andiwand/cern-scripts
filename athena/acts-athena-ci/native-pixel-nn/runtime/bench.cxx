#include "SiClusterizationTool/NativePixelClusterNN.h"
#include <onnxruntime_cxx_api.h>
#include <algorithm>
#include <array>
#include <cfenv>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <vector>
using NN=InDet::NativePixelClusterNN;
using Input=NN::InputVector;
int main(int argc,char** argv) try {
 if(argc<5)throw std::runtime_error("mode input count output/model-directory");
 const std::string mode=argv[1];const size_t count=std::stoul(argv[3]);
 std::ifstream source(argv[2],std::ios::binary|std::ios::ate);
 if(!source)throw std::runtime_error("Missing input");
 const size_t bytes=source.tellg();
 if(bytes%sizeof(Input) || bytes/sizeof(Input)<count)throw std::runtime_error("Bad input count");
 std::vector<Input> all(bytes/sizeof(Input)),input(count);source.seekg(0);source.read(reinterpret_cast<char*>(all.data()),bytes);
 for(size_t i=0;i<count;++i)input[i]=all[i*all.size()/count];
 Ort::Env env(ORT_LOGGING_LEVEL_WARNING,"native-bench");
 std::array<std::unique_ptr<const InDet::NativePixelClusterNN>,4> networks;
 const std::string models=argc>5 ? argv[5] : "/cvmfs/atlas.cern.ch/repo/sw/database/GroupData/ITkPixelClusterization/nn-01-01-01";
 for(unsigned i=0;i<4;++i)networks[i]=std::make_unique<const InDet::NativePixelClusterNN>(env,models+"/"+(i==0?"number":"pos"+std::to_string(i))+".onnx",NN::models[i],std::getenv("NATIVE_NN_FORCE_SSE")==nullptr);
 if(mode=="dump") {
  std::ofstream out(argv[4],std::ios::binary);std::feclearexcept(FE_ALL_EXCEPT);
  for(const auto& x:input){std::array<float,33> y;unsigned offset=0;for(unsigned i=0;i<4;++i){networks[i]->infer(x,std::span<float>(y.data()+offset,networks[i]->outputSize()));offset+=networks[i]->outputSize();}out.write(reinterpret_cast<char*>(y.data()),sizeof(y));}
  if(!out || std::fetestexcept(FE_INVALID|FE_DIVBYZERO|FE_OVERFLOW))throw std::runtime_error("Dump failed/FPE");
  return 0;
 }
 double checksum=0;
 auto one=[&](const Input& x){NN::NumberOutputVector p;NN::PositionOutputVector y;networks[0]->infer(x,p);unsigned n=std::max_element(p.begin(),p.end())-p.begin()+1;networks[n]->infer(x,std::span(y).first(networks[n]->outputSize()));checksum+=p[0]+y[1]+y[3]+n;};
 for(unsigned i=0;i<1000;++i)one(input[i%input.size()]);
 const unsigned repeats=std::getenv("NATIVE_NN_REPEATS") ? std::stoul(std::getenv("NATIVE_NN_REPEATS")) : 1;
 const auto start=std::chrono::steady_clock::now();for(unsigned r=0;r<repeats;++r)for(const auto& x:input)one(x);
 const double us=std::chrono::duration<double,std::micro>(std::chrono::steady_clock::now()-start).count()/(input.size()*repeats);
 std::cout<<std::setprecision(12)<<"{\"us\":"<<us<<",\"checksum\":"<<checksum<<"}\n";
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
