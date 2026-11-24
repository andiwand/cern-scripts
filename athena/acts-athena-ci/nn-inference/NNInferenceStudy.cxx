#include "NNInferenceStudy.h"
#include <onnxruntime_cxx_api.h>
#include <lwtnn/parse_json.hh>
#include <lwtnn/generic/Stack.hh>
#include <lwtnn/generic/Stack.tcc>
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <mutex>
#include <stdexcept>
#include <vector>
#include "TMVA/SOFIE_common.hxx"
namespace nnstudy {
// Equivalent sigmoid with no exponential overflow for finite inputs.
inline float sigmoid(float x) {
  const float e = std::exp(-std::abs(x));
  return x >= 0.f ? 1.f/(1.f+e) : e/(1.f+e);
}
// A batch-one GEMM is GEMV. Preserve generated arithmetic and tensor layout;
// retain the standard generator as a separate backend for comparison.
extern "C" void sgemv_(const char*,const int*,const int*,const float*,const float*,const int*,const float*,const int*,const float*,float*,const int*);
inline void gemvCall(float* y,bool ta,bool tb,int m,int n,int k,float alpha,const float* a,const float* x,float beta,const float* c) {
  if(n!=1 || tb) throw std::runtime_error("SOFIE GEMV specialization requires batch one");
  if(c) std::copy_n(c,m,y);
  const int rows=ta ? k : m,cols=ta ? m : k,inc=1;
  const char trans=ta ? 'T' : 'N';
  sgemv_(&trans,&rows,&cols,&alpha,a,&rows,x,&inc,&beta,y,&inc);
}
}
#include "number_sofie.hxx"
#include "pos1_sofie.hxx"
#include "pos2_sofie.hxx"
#include "pos3_sofie.hxx"
#include "number_sofie_gemv.hxx"
#include "pos1_sofie_gemv.hxx"
#include "pos2_sofie_gemv.hxx"
#include "pos3_sofie_gemv.hxx"

namespace nnstudy {
namespace {
const std::array<std::string,4> names{"number","pos1","pos2","pos3"};
unsigned outputs(unsigned m) { return m == 0 ? 3 : 5*m; }
std::string requiredEnv(const char* key) {
  const char* value=std::getenv(key);
  if (!value || !*value) throw std::runtime_error(std::string("Missing ")+key);
  return value;
}
struct Layer {
  unsigned in=0,out=0;
  std::vector<float> weights,bias; // column major: vectorize across outputs
};
using Network=std::array<Layer,5>;
Network loadBinary(const std::string& path,unsigned expected) {
  std::ifstream f(path,std::ios::binary);
  char magic[8]; std::uint32_t id;
  f.read(magic,8); f.read(reinterpret_cast<char*>(&id),4);
  if (!f || std::memcmp(magic,"NNSTUDY1",8) || id!=expected) throw std::runtime_error("Invalid weights "+path);
  Network net;
  const std::array<unsigned,6> dims{67,128,64,32,16,outputs(expected)};
  for (unsigned k=0;k<5;++k) {
    auto& l=net[k]; f.read(reinterpret_cast<char*>(&l.in),4); f.read(reinterpret_cast<char*>(&l.out),4);
    if(l.in!=dims[k] || l.out!=dims[k+1]) throw std::runtime_error("Invalid architecture "+path);
    std::vector<float> row(l.in*l.out); l.weights.resize(row.size()); l.bias.resize(l.out);
    f.read(reinterpret_cast<char*>(row.data()),row.size()*4);
    f.read(reinterpret_cast<char*>(l.bias.data()),l.bias.size()*4);
    for(unsigned i=0;i<l.out;++i) for(unsigned j=0;j<l.in;++j) l.weights[j*l.out+i]=row[i*l.in+j];
  }
  if(!f || f.peek()!=std::char_traits<char>::eof()) throw std::runtime_error("Truncated/extended weights "+path);
  return net;
}
template<unsigned In,unsigned Out>
void dense(const Layer& l,const float* __restrict x,float* __restrict y) {
  std::copy_n(l.bias.data(),Out,y);
  for(unsigned j=0;j<In;++j) {
    const float a=x[j]; const float* w=l.weights.data()+j*Out;
    for(unsigned i=0;i<Out;++i) y[i]+=a*w[i];
  }
}
template<unsigned In,unsigned Out>
__attribute__((target("avx2,fma")))
void denseAvx2(const Layer& l,const float* __restrict x,float* __restrict y) {
  std::copy_n(l.bias.data(),Out,y);
  for(unsigned j=0;j<In;++j) {
    const float a=x[j]; const float* w=l.weights.data()+j*Out;
    for(unsigned i=0;i<Out;++i) y[i]+=a*w[i];
  }
}
void normalize(const float* input,float* output) {
  for(unsigned i=0;i<67;++i) output[i]=i<49 ? input[i]*1e-5f : input[i];
}
void activate(float* x,unsigned n) {
  for(unsigned i=0;i<n;++i) x[i]*=sigmoid(x[i]);
}
void finish(unsigned model,float* out) {
  const unsigned n=model==0 ? 3 : model;
  const unsigned stride=model==0 ? 1 : 5;
  float maximum=out[0];
  for(unsigned i=1;i<n;++i) maximum=std::max(maximum,out[stride*i]);
  float sum=0;
  for(unsigned i=0;i<n;++i) { out[stride*i]=std::exp(out[stride*i]-maximum); sum+=out[stride*i]; }
  for(unsigned i=0;i<n;++i) out[stride*i]/=sum;
  if(model) for(unsigned i=0;i<model;++i) for(unsigned k=3;k<5;++k) {
    const float p=std::abs(out[5*i+k])+1e-4f;
    out[5*i+k]=p*p;
  }
}
struct OrtNetwork {
  Ort::Session session;
  Ort::MemoryInfo memory=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
  std::array<float,67> input{};
  std::array<float,15> output{};
  std::array<int64_t,2> inputShape{1,67},outputShape;
  Ort::Value inputTensor{nullptr},outputTensor{nullptr};
  std::string inputName,outputName;
  OrtNetwork(Ort::Env& env,const std::string& path,unsigned model,const std::string& optimized):session(nullptr),outputShape{1,outputs(model)} {
    Ort::SessionOptions options;
    options.SetIntraOpNumThreads(1); options.SetInterOpNumThreads(1);
    options.SetGraphOptimizationLevel(ORT_ENABLE_ALL);
    options.DisablePerSessionThreads();
    if(!optimized.empty()) options.SetOptimizedModelFilePath(optimized.c_str());
    session=Ort::Session(env,path.c_str(),options);
    Ort::AllocatorWithDefaultOptions allocator;
    inputName=session.GetInputNameAllocated(0,allocator).get();
    outputName=session.GetOutputNameAllocated(0,allocator).get();
    inputTensor=Ort::Value::CreateTensor<float>(memory,input.data(),input.size(),inputShape.data(),2);
    outputTensor=Ort::Value::CreateTensor<float>(memory,output.data(),outputs(model),outputShape.data(),2);
  }
  void runCached(const float* x,float* y,unsigned n) {
    std::copy_n(x,67,input.data());
    const char* ins=inputName.c_str(); const char* outs=outputName.c_str();
    session.Run(Ort::RunOptions{nullptr},&ins,&inputTensor,1,&outs,&outputTensor,1);
    std::copy_n(output.data(),n,y);
  }
  void runOriginal(const float* x,float* y,unsigned model) {
    auto inputType=session.GetInputTypeInfo(0);
    auto info=inputType.GetTensorTypeAndShapeInfo();
    const int64_t dim=info.GetShape()[1];
    auto mem=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);
    std::vector<int64_t> shape{1,dim};
    auto tensor=Ort::Value::CreateTensor<float>(mem,const_cast<float*>(x),67,shape.data(),shape.size());
    Ort::AllocatorWithDefaultOptions allocator;
    auto in=session.GetInputNameAllocated(0,allocator);
    auto out=session.GetOutputNameAllocated(0,allocator);
    const char* ip=in.get(); const char* op=out.get();
    if(model) { auto ot=session.GetOutputTypeInfo(0); auto ti=ot.GetTensorTypeAndShapeInfo(); auto s=ti.GetShape(); (void)s; }
    auto result=session.Run(Ort::RunOptions{nullptr},&ip,&tensor,1,&op,1);
    std::copy_n(result[0].GetTensorData<float>(),outputs(model),y);
  }
};
}
struct Engine::Impl {
  std::string backend;
  std::unique_ptr<Ort::Env> env;
  std::array<std::unique_ptr<OrtNetwork>,4> ort;
  std::array<Network,4> direct;
  std::array<std::unique_ptr<lwt::generic::Stack<float>>,4> lw;
  std::array<std::unique_ptr<lwt::generic::Stack<double>>,4> lwd;
  std::unique_ptr<TMVA_SOFIE_number_simple::Session> s0;
  std::unique_ptr<TMVA_SOFIE_pos1_simple::Session> s1;
  std::unique_ptr<TMVA_SOFIE_pos2_simple::Session> s2;
  std::unique_ptr<TMVA_SOFIE_pos3_simple::Session> s3;
  std::unique_ptr<TMVA_SOFIE_number_simple_gemv::Session> g0;
  std::unique_ptr<TMVA_SOFIE_pos1_simple_gemv::Session> g1;
  std::unique_ptr<TMVA_SOFIE_pos2_simple_gemv::Session> g2;
  std::unique_ptr<TMVA_SOFIE_pos3_simple_gemv::Session> g3;
  explicit Impl(const std::string& b,const std::string& d):backend(b) {
    if(b=="original" || b=="ort_cached" || b=="ort_simple") {
      Ort::ThreadingOptions threads; threads.SetGlobalIntraOpNumThreads(1); threads.SetGlobalInterOpNumThreads(1);
      env=std::make_unique<Ort::Env>(threads,ORT_LOGGING_LEVEL_WARNING,"nn-study");
      for(unsigned m=0;m<4;++m) {
        const auto path=d+"/"+names[m]+(b=="ort_simple" ? "_simple.onnx" : ".onnx");
        const char* save=std::getenv("NN_STUDY_SAVE_OPTIMIZED");
        ort[m]=std::make_unique<OrtNetwork>(*env,path,m,save ? std::string(save)+"/"+names[m]+"_"+b+".onnx" : "");
      }
    } else if(b=="direct" || b=="direct_avx2") {
      if(b=="direct_avx2" && !__builtin_cpu_supports("avx2")) throw std::runtime_error("AVX2 unavailable");
      for(unsigned m=0;m<4;++m) direct[m]=loadBinary(d+"/"+names[m]+".bin",m);
    } else if(b=="lwtnn" || b=="lwtnn_double") {
      for(unsigned m=0;m<4;++m) {
        std::ifstream stream(d+"/"+names[m]+".json"); auto config=lwt::parse_json(stream);
        if(b=="lwtnn") lw[m]=std::make_unique<lwt::generic::Stack<float>>(67,config.layers);
        else lwd[m]=std::make_unique<lwt::generic::Stack<double>>(67,config.layers);
      }
    } else if(b=="sofie") {
      s0=std::make_unique<TMVA_SOFIE_number_simple::Session>(d+"/number_sofie.dat");
      s1=std::make_unique<TMVA_SOFIE_pos1_simple::Session>(d+"/pos1_sofie.dat");
      s2=std::make_unique<TMVA_SOFIE_pos2_simple::Session>(d+"/pos2_sofie.dat");
      s3=std::make_unique<TMVA_SOFIE_pos3_simple::Session>(d+"/pos3_sofie.dat");
    } else if(b=="sofie_gemv") {
      g0=std::make_unique<TMVA_SOFIE_number_simple_gemv::Session>(d+"/number_sofie.dat");
      g1=std::make_unique<TMVA_SOFIE_pos1_simple_gemv::Session>(d+"/pos1_sofie.dat");
      g2=std::make_unique<TMVA_SOFIE_pos2_simple_gemv::Session>(d+"/pos2_sofie.dat");
      g3=std::make_unique<TMVA_SOFIE_pos3_simple_gemv::Session>(d+"/pos3_sofie.dat");
    } else throw std::runtime_error("Unknown backend "+b);
  }
  void infer(unsigned m,const float* x,float* y) {
    if(m>3) throw std::runtime_error("Invalid model");
    if(ort[m]) {
      if(backend=="original") ort[m]->runOriginal(x,y,m);
      else ort[m]->runCached(x,y,outputs(m));
      return;
    }
    if(s0) {
      switch(m) {
        case 0: TMVA_SOFIE_number_simple::doInfer(*s0,x,y); break;
        case 1: TMVA_SOFIE_pos1_simple::doInfer(*s1,x,y); break;
        case 2: TMVA_SOFIE_pos2_simple::doInfer(*s2,x,y); break;
        case 3: TMVA_SOFIE_pos3_simple::doInfer(*s3,x,y); break;
      }
      return;
    }
    if(g0) {
      switch(m) {
        case 0: TMVA_SOFIE_number_simple_gemv::doInfer(*g0,x,y); break;
        case 1: TMVA_SOFIE_pos1_simple_gemv::doInfer(*g1,x,y); break;
        case 2: TMVA_SOFIE_pos2_simple_gemv::doInfer(*g2,x,y); break;
        case 3: TMVA_SOFIE_pos3_simple_gemv::doInfer(*g3,x,y); break;
      }
      return;
    }
    alignas(64) float a[128],b[128]; normalize(x,a);
    if(lw[m]) {
      Eigen::VectorXf v=Eigen::Map<Eigen::VectorXf>(a,67);
      auto result=lw[m]->compute(std::move(v)); std::copy_n(result.data(),outputs(m),y);
    } else if(lwd[m]) {
      Eigen::VectorXd v=Eigen::Map<Eigen::VectorXf>(a,67).cast<double>();
      auto result=lwd[m]->compute(std::move(v));
      for(unsigned i=0;i<outputs(m);++i) y[i]=result[i];
    } else {
      const auto& n=direct[m]; const bool avx=backend=="direct_avx2";
      (avx ? denseAvx2<67,128> : dense<67,128>)(n[0],a,b); activate(b,128);
      (avx ? denseAvx2<128,64> : dense<128,64>)(n[1],b,a); activate(a,64);
      (avx ? denseAvx2<64,32> : dense<64,32>)(n[2],a,b); activate(b,32);
      (avx ? denseAvx2<32,16> : dense<32,16>)(n[3],b,a);
      switch(m) {
        case 0: (avx ? denseAvx2<16,3> : dense<16,3>)(n[4],a,y); break;
        case 1: (avx ? denseAvx2<16,5> : dense<16,5>)(n[4],a,y); break;
        case 2: (avx ? denseAvx2<16,10> : dense<16,10>)(n[4],a,y); break;
        case 3: (avx ? denseAvx2<16,15> : dense<16,15>)(n[4],a,y); break;
      }
    }
    finish(m,y);
  }
};
Engine::Engine(const std::string& b,const std::string& d):m_impl(std::make_unique<Impl>(b,d)){}
Engine::~Engine()=default;
void Engine::infer(unsigned m,const float* x,float* y){m_impl->infer(m,x,y);}
bool replacementEnabled() {
  static const bool enabled=[] { const char* b=std::getenv("NN_STUDY_BACKEND"); return b && std::string(b)!="original"; }();
  return enabled;
}
void infer(unsigned m,const float* x,float* y) {
  thread_local Engine engine(requiredEnv("NN_STUDY_BACKEND"),requiredEnv("NN_STUDY_MODEL_DIR"));
  engine.infer(m,x,y);
}
void capture(const float* input) {
  static const char* path=std::getenv("NN_STUDY_CAPTURE");
  if(!path || !*path) return;
  static std::mutex mutex;
  static std::ofstream f(path,std::ios::binary);
  std::lock_guard<std::mutex> lock(mutex);
  f.write(reinterpret_cast<const char*>(input),67*sizeof(float));
  if(!f) throw std::runtime_error("Failed writing captured inputs");
}
bool profilingEnabled() {
  static const bool enabled = std::getenv("NN_STUDY_PROFILE") != nullptr;
  return enabled;
}
void recordProfile(unsigned stage,std::uint64_t ns) {
  struct Stats {
    std::array<std::uint64_t,4> counts{},nanoseconds{};
    ~Stats() {
      static auto* mutex = new std::mutex;
      std::lock_guard<std::mutex> lock(*mutex);
      std::ofstream out(std::getenv("NN_STUDY_PROFILE"),std::ios::app);
      out << "{\"backend\":\"" << std::getenv("NN_STUDY_BACKEND") << "\",\"counts\":[";
      for(unsigned i=0;i<4;++i) out << (i ? "," : "") << counts[i];
      out << "],\"nanoseconds\":[";
      for(unsigned i=0;i<4;++i) out << (i ? "," : "") << nanoseconds[i];
      out << "]}\n";
    }
  };
  thread_local Stats stats;
  ++stats.counts.at(stage);
  stats.nanoseconds.at(stage)+=ns;
}
}
