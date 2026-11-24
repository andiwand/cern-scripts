#include <Eigen/Core>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <utility>
#include <vector>
#ifdef __AVX2__
constexpr unsigned lanes=8;
#else
constexpr unsigned lanes=4;
#endif
using Packet=Eigen::Array<float,lanes,1>;
using Clock=std::chrono::steady_clock;
template<size_t... I> inline void update(std::array<Packet,12>& a,const Packet& b,const Packet& c,std::index_sequence<I...>){((a[I]=a[I]*b+c),...);}
__attribute__((noinline)) double compute(unsigned repetitions,float seed){
 std::array<Packet,12> a;for(unsigned i=0;i<a.size();++i)a[i]=Packet::Constant(seed+i*.001f);
 const Packet b=Packet::Constant(.999999f),c=Packet::Constant(.000001f);
 for(unsigned i=0;i<repetitions;++i)update(a,b,c,std::make_index_sequence<12>{});
 double sum=0;for(const auto& p:a)sum+=p.sum();return sum;
}
template<size_t... I> inline void load(std::array<Packet,8>& a,const float* data,std::index_sequence<I...>){((a[I]+=Eigen::Map<const Packet>(data+I*lanes)),...);}
__attribute__((noinline)) double read(const float* data,size_t size,unsigned repetitions){
 std::array<Packet,8> a;for(auto& p:a)p.setZero();
 for(unsigned r=0;r<repetitions;++r){
  asm volatile(""::"r"(data):"memory");
  for(size_t i=0;i<size;i+=8*lanes)load(a,data+i,std::make_index_sequence<8>{});
 }
 double sum=0;for(const auto& p:a)sum+=p.sum();return sum;
}
int main(int argc,char** argv){
 const float seed=argc>1?std::atof(argv[1]):.5f;double checksum=0;
 std::cout<<std::setprecision(12);
 for(unsigned cycle=0;cycle<3;++cycle){
  const unsigned repeats=100000000;
  auto start=Clock::now();checksum+=compute(repeats,seed+cycle*.001f);
  const double seconds=std::chrono::duration<double>(Clock::now()-start).count();
  std::cout<<"{\"kind\":\"compute\",\"lanes\":"<<lanes<<",\"cycle\":"<<cycle<<",\"gflops\":"<<double(repeats)*12*lanes*2/seconds/1e9<<"}\n";
 }
 for(size_t bytes:{size_t(16384),size_t(32768),size_t(65536),size_t(131072),size_t(262144),size_t(524288),size_t(1048576),size_t(8388608),size_t(33554432),size_t(134217728)}){
  std::vector<float> data(bytes/4,seed);const unsigned repeats=std::max(size_t(10),size_t(4)*1024*1024*1024/bytes);
  checksum+=read(data.data(),data.size(),1);
  for(unsigned cycle=0;cycle<3;++cycle){
   auto start=Clock::now();checksum+=read(data.data(),data.size(),repeats);
   const double seconds=std::chrono::duration<double>(Clock::now()-start).count();
   std::cout<<"{\"kind\":\"read\",\"lanes\":"<<lanes<<",\"cycle\":"<<cycle<<",\"bytes\":"<<bytes<<",\"GBps\":"<<double(bytes)*repeats/seconds/1e9<<"}\n";
  }
 }
 std::cerr<<"checksum "<<checksum<<'\n';
}
