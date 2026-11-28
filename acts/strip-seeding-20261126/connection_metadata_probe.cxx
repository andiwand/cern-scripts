// Local study validation; intentionally outside the merge request.
#include "src/GbtsConnectionTuning.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <vector>

int main(int argc, char** argv) {
  using namespace Acts::Experimental;
  using ActsTrk::detail::applyStripConnectionTauCuts;
  auto check=[](bool ok) { if (!ok) throw std::runtime_error("Metadata-cut regression"); };
  check(argc==2);
  std::ifstream input(argv[1]);unsigned nl{},nc{};input>>nl>>nc;
  std::vector<GbtsLayerDescription> layers(nl);
  for(auto& l:layers){unsigned type{},technology{};input>>l.id>>type>>technology;l.type=GbtsLayerType(type);l.technology=GbtsLayerTechnology(technology);}
  std::vector<GbtsLayerConnection> expected(nc);
  for(auto& c:expected)input>>c.src>>c.dst>>c.tauRatioCutInner>>c.tauRatioCutOuter;
  check(bool(input)&&nc==31);
  const std::map<std::string,double> cuts{{"barrel-barrel",.020},{"barrel-endcap",.025},{"endcap-endcap",.035}};
  auto same=[&](const auto& actual,const auto& want){check(actual.size()==want.size());for(unsigned i=0;i<actual.size();++i)check(actual[i].src==want[i].src&&actual[i].dst==want[i].dst&&actual[i].tauRatioCutInner==want[i].tauRatioCutInner&&actual[i].tauRatioCutOuter==want[i].tauRatioCutOuter);};
  auto raw=expected;for(auto& c:raw){c.tauRatioCutInner=.044f;c.tauRatioCutOuter=.044f;}
  auto actual=raw;applyStripConnectionTauCuts(actual,layers,cuts);same(actual,expected);
  auto disabled=raw;applyStripConnectionTauCuts(disabled,layers,{});same(disabled,raw);
  auto renamedLayers=layers;auto renamed=raw;auto renamedExpected=expected;std::map<unsigned,unsigned> ids;
  for(unsigned i=0;i<nl;++i){ids[layers[i].id]=1000003+97*i;renamedLayers[i].id=ids.at(layers[i].id);}
  for(auto* v:{&renamed,&renamedExpected})for(auto& c:*v){c.src=ids.at(c.src);c.dst=ids.at(c.dst);}
  applyStripConnectionTauCuts(renamed,renamedLayers,cuts);same(renamed,renamedExpected);
  auto reversed=raw;auto reversedExpected=expected;for(auto* v:{&reversed,&reversedExpected})for(auto& c:*v)std::swap(c.src,c.dst);
  applyStripConnectionTauCuts(reversed,layers,cuts);same(reversed,reversedExpected);
  const auto pixel=std::ranges::find(layers,GbtsLayerTechnology::Pixel,&GbtsLayerDescription::technology);
  const auto strip=std::ranges::find(layers,GbtsLayerTechnology::Strip,&GbtsLayerDescription::technology);
  std::vector<GbtsLayerConnection> other{{pixel->id,pixel->id,.011f,.022f},{pixel->id,strip->id,.033f,.044f}};
  const auto before=other;applyStripConnectionTauCuts(other,layers,cuts);same(other,before);
  for(const auto& bad:std::vector<std::map<std::string,double>>{{{"typo",.02f}},{{"barrel-barrel",0.f}},{{"barrel-endcap",-.01f}},{{"endcap-endcap",std::numeric_limits<float>::quiet_NaN()}}}){
    bool rejected=false;try{applyStripConnectionTauCuts(actual,layers,bad);}catch(const std::invalid_argument&){rejected=true;}check(rejected);
  }
  std::cout<<"All 31 cuts match exactly; arbitrary layer-ID renumbering and reversed links agree; empty settings, pixel/mixed links and invalid cuts checked.\n";
}
