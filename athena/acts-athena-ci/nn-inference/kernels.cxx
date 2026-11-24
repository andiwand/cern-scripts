// Diagnostic only: compare existing dense kernels and activation work separately.
#include "NNInferenceStudy.cxx"
#include <chrono>
#include <iomanip>
#include <iostream>
#include <xmmintrin.h>

using Clock = std::chrono::steady_clock;
using Input = std::array<float,67>;

template<unsigned In,unsigned Out>
__attribute__((noinline))
void directKernel(const nnstudy::Layer& l,const float* __restrict x,float* __restrict y) {
  nnstudy::dense<In,Out>(l,x,y);
}
template<unsigned In,unsigned Out>
__attribute__((noinline))
void avxKernel(const nnstudy::Layer& l,const float* __restrict x,float* __restrict y) {
  nnstudy::denseAvx2<In,Out>(l,x,y);
}
// Diagnostic intervention: keep 16 output accumulators in four SSE registers.
// The input accumulation order is unchanged. This is not an integrated backend.
template<unsigned In,unsigned Out>
__attribute__((noinline))
void blockedKernel(const nnstudy::Layer& l,const float* x,float* y) {
  if constexpr(Out<16) { nnstudy::dense<In,Out>(l,x,y); return; }
  static_assert(Out<16 || Out%16==0);
  for(unsigned i=0;i+16<=Out;i+=16) {
    __m128 a0=_mm_loadu_ps(l.bias.data()+i),a1=_mm_loadu_ps(l.bias.data()+i+4);
    __m128 a2=_mm_loadu_ps(l.bias.data()+i+8),a3=_mm_loadu_ps(l.bias.data()+i+12);
    for(unsigned j=0;j<In;++j) {
      const auto v=_mm_set1_ps(x[j]);const float* w=l.weights.data()+j*Out+i;
      a0=_mm_add_ps(a0,_mm_mul_ps(v,_mm_loadu_ps(w)));
      a1=_mm_add_ps(a1,_mm_mul_ps(v,_mm_loadu_ps(w+4)));
      a2=_mm_add_ps(a2,_mm_mul_ps(v,_mm_loadu_ps(w+8)));
      a3=_mm_add_ps(a3,_mm_mul_ps(v,_mm_loadu_ps(w+12)));
    }
    _mm_storeu_ps(y+i,a0);_mm_storeu_ps(y+i+4,a1);
    _mm_storeu_ps(y+i+8,a2);_mm_storeu_ps(y+i+12,a3);
  }
}
__attribute__((noinline))
void blasKernel(const nnstudy::Layer& l,const float* row,const float* x,float* y) {
  nnstudy::gemvCall(y,true,false,l.out,1,l.in,1.f,row,x,1.f,l.bias.data());
}
volatile double sink = 0;
template<class F>
double bench(F&& function,const std::vector<float>& inputs,unsigned in,unsigned out) {
  constexpr unsigned calls=100000;
  std::array<float,128> y{};double sum=0;
  const auto n=inputs.size()/in;
  for(unsigned k=0;k<1000;++k) function(inputs.data()+(k%n)*in,y.data());
  const auto start=Clock::now();
  for(unsigned k=0;k<calls;++k) {
    function(inputs.data()+(k%n)*in,y.data());
    sum+=y[k%out];
  }
  const double us=std::chrono::duration<double>(Clock::now()-start).count()*1e6/calls;
  sink=sum;return us;
}

template<unsigned In,unsigned Out>
void layer(const nnstudy::Layer& l,const std::vector<float>& inputs,unsigned model,unsigned index) {
  std::vector<float> row(In*Out);
  for(unsigned i=0;i<Out;++i) for(unsigned j=0;j<In;++j) row[i*In+j]=l.weights[j*Out+i];
  const double baseline=bench([](const float* x,float* y){for(unsigned i=0;i<Out;++i)y[i]=x[0];},inputs,In,Out);
  auto direct=[&](const float* x,float* y){directKernel<In,Out>(l,x,y);};
  auto avx=[&](const float* x,float* y){avxKernel<In,Out>(l,x,y);};
  auto blocked=[&](const float* x,float* y){blockedKernel<In,Out>(l,x,y);};
  auto blas=[&](const float* x,float* y){blasKernel(l,row.data(),x,y);};
  double maxScaled=0;
  std::vector<float> activations;activations.reserve(inputs.size()/In*Out);
  for(unsigned i=0;i<inputs.size()/In;++i) {
    std::array<float,128> d{},b{},s{};direct(inputs.data()+i*In,d.data());blas(inputs.data()+i*In,b.data());blocked(inputs.data()+i*In,s.data());
    if(std::memcmp(d.data(),s.data(),Out*sizeof(float)))throw std::runtime_error("Blocked SSE changed accumulation results");
    for(unsigned j=0;j<Out;++j)maxScaled=std::max(maxScaled,std::abs(double(d[j])-b[j])/(1+std::abs(double(d[j]))));
    activations.insert(activations.end(),d.begin(),d.begin()+Out);
  }
  std::cout<<"{\"model\":"<<model<<",\"layer\":"<<index<<",\"in\":"<<In<<",\"out\":"<<Out
           <<",\"mxcsr\":"<<_mm_getcsr()<<",\"subnormal_inputs\":"
           <<std::count_if(inputs.begin(),inputs.end(),[](float x){return std::fpclassify(x)==FP_SUBNORMAL;})
           <<",\"input_values\":"<<inputs.size()
           <<",\"baseline_us\":"<<baseline<<",\"max_scaled_blas_difference\":"<<maxScaled<<",\"dense_raw_us\":[";
  for(unsigned cycle=0;cycle<3;++cycle) {
    double d,b,a;
    if(cycle==1){b=bench(blas,inputs,In,Out);a=bench(avx,inputs,In,Out);d=bench(direct,inputs,In,Out);}
    else {d=bench(direct,inputs,In,Out);a=bench(avx,inputs,In,Out);b=bench(blas,inputs,In,Out);}
    const double blockedTime=bench(blocked,inputs,In,Out);
    std::cout<<(cycle ? "," : "")<<"{\"sse\":"<<d<<",\"avx2\":"<<a<<",\"gemv\":"<<b<<",\"sse_blocked\":"<<blockedTime<<"}";
  }
  std::cout<<"]";
  if(index<3) {
    const double fused=bench([](const float* x,float* y){std::copy_n(x,Out,y);nnstudy::activate(y,Out);},activations,Out,Out);
    const double separate=bench([](const float* x,float* y){std::array<float,Out> tmp;for(unsigned i=0;i<Out;++i)tmp[i]=nnstudy::sigmoid(x[i]);for(unsigned i=0;i<Out;++i)y[i]=x[i]*tmp[i];},activations,Out,Out);
    std::cout<<",\"activation_us\":{\"direct_fused\":"<<fused<<",\"sofie_separate\":"<<separate<<"}";
  }
  std::cout<<"}\n"<<std::flush;
}

int main() try {
  if(!__builtin_cpu_supports("avx2") || !__builtin_cpu_supports("fma"))
    throw std::runtime_error("This diagnostic compares AVX2/FMA and needs both CPU features");
  const std::string root=std::getenv("NN_STUDY_ROOT");
  std::ifstream stream(root+"/captured-inputs.bin",std::ios::binary|std::ios::ate);
  const std::size_t count=stream.tellg()/sizeof(Input);
  std::array<Input,512> captured;
  for(unsigned i=0;i<captured.size();++i){stream.seekg(i*count/captured.size()*sizeof(Input));stream.read(reinterpret_cast<char*>(captured[i].data()),sizeof(Input));}
  if(!stream)throw std::runtime_error("Invalid captured inputs");
  std::cout<<std::setprecision(10);
  for(unsigned model=0;model<2;++model) {
    const auto net=nnstudy::loadBinary(root+"/models/"+(model==0 ? "number" : "pos1")+".bin",model);
    std::array<std::vector<float>,5> inputs;
    for(const auto& raw:captured) {
      std::array<float,128> a{},b{};nnstudy::normalize(raw.data(),a.data());
      for(unsigned index=0;index<5;++index) {
        const auto& l=net[index];inputs[index].insert(inputs[index].end(),a.begin(),a.begin()+l.in);
        switch(index) {
          case 0:nnstudy::dense<67,128>(l,a.data(),b.data());break;
          case 1:nnstudy::dense<128,64>(l,a.data(),b.data());break;
          case 2:nnstudy::dense<64,32>(l,a.data(),b.data());break;
          case 3:nnstudy::dense<32,16>(l,a.data(),b.data());break;
          case 4:break;
        }
        if(index<3)nnstudy::activate(b.data(),l.out);
        a=b;
      }
    }
    layer<67,128>(net[0],inputs[0],model,0);
    layer<128,64>(net[1],inputs[1],model,1);
    layer<64,32>(net[2],inputs[2],model,2);
    layer<32,16>(net[3],inputs[3],model,3);
    if(model==0)layer<16,3>(net[4],inputs[4],model,4);
    else layer<16,5>(net[4],inputs[4],model,4);
  }
  return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
