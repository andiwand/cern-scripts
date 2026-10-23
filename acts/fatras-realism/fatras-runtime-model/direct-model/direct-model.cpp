// Standalone feasibility probe, not a production Fatras implementation.
// Geant4 11.3.x component choices follow its FTFP_BERT builders.
#include <CLHEP/Random/JamesRandom.h>
#include <G4BGGNucleonInelasticXS.hh>
#include <G4BGGPionInelasticXS.hh>
#include <G4BaryonConstructor.hh>
#include <G4BosonConstructor.hh>
#include <G4CascadeInterface.hh>
#include <G4ComponentAntiNuclNuclearXS.hh>
#include <G4ComponentGGHadronNucleusXsc.hh>
#include <G4CrossSectionDataSetRegistry.hh>
#include <G4CrossSectionDataStore.hh>
#include <G4CrossSectionInelastic.hh>
#include <G4EnergyRangeManager.hh>
#include <G4ExcitedStringDecay.hh>
#include <G4FTFModel.hh>
#include <G4GeneratorPrecompoundInterface.hh>
#include <G4GenericIon.hh>
#include <G4HadronicInteractionRegistry.hh>
#include <G4HadronicParameters.hh>
#include <G4IonConstructor.hh>
#include <G4IonTable.hh>
#include <G4LeptonConstructor.hh>
#include <G4MesonConstructor.hh>
#include <G4NeutronInelasticXS.hh>
#include <G4NistManager.hh>
#include <G4NucleiProperties.hh>
#include <G4ParticleTable.hh>
#include <G4ParticlesWorkspace.hh>
#include <G4PhysicsModelCatalog.hh>
#include <G4ProcessManager.hh>
#include <G4ShortLivedConstructor.hh>
#include <G4StateManager.hh>
#include <G4SystemOfUnits.hh>
#include <G4TheoFSGenerator.hh>
#include <G4Threading.hh>
#include <G4Version.hh>
#include <Randomize.hh>
#include <algorithm>
#include <array>
#include <atomic>
#include <barrier>
#include <bit>
#include <chrono>
#include <cmath>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <sys/resource.h>
#include <thread>
#include <vector>

#ifndef G4MULTITHREADED
#error "This prototype requires an MT-enabled Geant4 build"
#endif

constexpr std::array<int, 9> pdgs{211,   -211,  2212, 2112, 130,
                                  -2212, -2112, 321,  -321};
constexpr std::array<double, 9> momenta{.05, .2, .5, 2., 4., 5., 6., 10., 100.};
G4ThreeVector directionFor(size_t index) {
  return std::array<G4ThreeVector, 3>{
      {{0, 0, 1},
       {1, 2, 3},
       {-1, 0, 0}}}[(index / (pdgs.size() * momenta.size())) % 3]
      .unit();
}
struct Product {
  int pdg;
  double mass, charge;
  G4ThreeVector p;
};
struct Event {
  double rate = 0, targetMass = 0, edep = 0;
  int a = 0, z = 0, status = 0;
  bool ftf = false;
  unsigned offShell = 0;
  double finalEnergyError = 0, finalMomentumError = 0, finalChargeError = 0;
  bool catastrophic = false;
  std::vector<Product> products;
  std::uint64_t hash() const {
    std::uint64_t h = 14695981039346656037ULL;
    auto add = [&](std::uint64_t x) {
      for (unsigned i = 0; i < 8; ++i) {
        h ^= (x >> (8 * i)) & 255;
        h *= 1099511628211ULL;
      }
    };
    auto real = [&](double x) { add(std::bit_cast<std::uint64_t>(x)); };
    real(rate);
    real(targetMass);
    real(edep);
    add(a);
    add(z);
    add(status);
    add(ftf);
    add(products.size());
    add(offShell);
    add(catastrophic);
    for (auto &p : products) {
      add(p.pdg);
      real(p.mass);
      real(p.charge);
      real(p.p.x());
      real(p.p.y());
      real(p.p.z());
    }
    return h;
  }
};
struct ScopedEngine {
  CLHEP::HepRandomEngine *previous = G4Random::getTheEngine();
  std::vector<unsigned long> state = previous->put();
  CLHEP::HepJamesRandom engine;
  explicit ScopedEngine(long seed) : engine(seed) {
    G4Random::setTheEngine(&engine);
  }
  ~ScopedEngine() { G4Random::setTheEngine(previous); }
  void verify() const {
    if (previous->put() != state)
      throw std::runtime_error("caller RNG state changed");
  }
};
struct Models {
  // Registries own the model/data graphs; clean on their creating thread.
  G4CascadeInterface *bert = new G4CascadeInterface;
  G4TheoFSGenerator *ftfp = new G4TheoFSGenerator("FTFP");
  std::array<G4CrossSectionDataStore, 9> xs;
  G4EnergyRangeManager selection;
  Models() {
    auto *par = G4HadronicParameters::Instance();
    bert->SetMinEnergy(0);
    bert->SetMaxEnergy(par->GetMaxEnergyTransitionFTF_Cascade());
    ftfp->SetMinEnergy(par->GetMinEnergyTransitionFTF_Cascade());
    ftfp->SetMaxEnergy(par->GetMaxEnergy());
    auto *ftf = new G4FTFModel;
    ftf->SetFragmentationModel(new G4ExcitedStringDecay);
    ftfp->SetHighEnergyGenerator(ftf);
    ftfp->SetTransport(new G4GeneratorPrecompoundInterface);
    selection.RegisterMe(ftfp);
    selection.RegisterMe(bert);
    for (size_t i = 0; i < pdgs.size(); ++i) {
      auto *p = G4ParticleTable::GetParticleTable()->FindParticle(pdgs[i]);
      G4VCrossSectionDataSet *data;
      if (std::abs(pdgs[i]) == 211)
        data = new G4BGGPionInelasticXS(p);
      else if (pdgs[i] == 2212)
        data = new G4BGGNucleonInelasticXS(p);
      else if (pdgs[i] == 2112)
        data = new G4NeutronInelasticXS;
      else if (pdgs[i] < -2000)
        data = new G4CrossSectionInelastic(new G4ComponentAntiNuclNuclearXS);
      else
        data = new G4CrossSectionInelastic(new G4ComponentGGHadronNucleusXsc);
      xs[i].SetVerboseLevel(0);
      xs[i].AddDataSet(data);
      xs[i].BuildPhysicsTable(*p);
      bert->BuildPhysicsTable(*p);
      ftfp->BuildPhysicsTable(*p);
    }
    G4HadronicInteractionRegistry::Instance()->InitialiseModels();
  }
  ~Models() {
    G4HadronicInteractionRegistry::Instance()->Clean();
    G4CrossSectionDataSetRegistry::Instance()->Clean();
  }
  Event sample(G4Material *mat, size_t index, long seedOffset) {
    const size_t k = index % pdgs.size();
    auto *p = G4ParticleTable::GetParticleTable()->FindParticle(pdgs[k]);
    const double mom =
        momenta[(index / pdgs.size()) % momenta.size()] * CLHEP::GeV;
    const double ke =
        mom * mom / (std::hypot(mom, p->GetPDGMass()) + p->GetPDGMass());
    // Non-axial projectiles exercise frame transformations.
    const auto direction = directionFor(index);
    ScopedEngine rng(seedOffset + static_cast<long>(index));
    G4DynamicParticle part(p, direction, ke);
    Event event;
    event.rate =
        xs[k].ComputeCrossSection(&part, mat) * mat->GetNuclearInterLength();
    if (!std::isfinite(event.rate) || event.rate < 0)
      throw std::runtime_error("invalid rate");
    if (event.rate <= 0) {
      rng.verify();
      return event;
    }
    G4Nucleus target;
    const auto *element = xs[k].SampleZandA(&part, mat, target);
    G4HadProjectile proj(part);
    auto *model =
        pdgs[k] < -2000
            ? ftfp
            : selection.GetHadronicInteraction(proj, target, mat, element);
    if (!model)
      throw std::runtime_error("no applicable hadronic model");
    event.ftf = model == ftfp;
    event.a = target.GetA_asInt();
    event.z = target.GetZ_asInt();
    event.targetMass = G4NucleiProperties::GetNuclearMass(event.a, event.z);
    auto *result = model->ApplyYourself(proj, target);
    if (!result)
      throw std::runtime_error("null final-state pointer");
    struct Clear {
      G4HadFinalState *result;
      ~Clear() {
        for (size_t i = 0; i < result->GetNumberOfSecondaries(); ++i)
          delete result->GetSecondary(i)->GetParticle();
        result->Clear();
      }
    } clear{result};
    event.status = result->GetStatusChange();
    event.edep = result->GetLocalEnergyDeposit();
    auto add = [&](G4DynamicParticle d) {
      // Match G4HadronicProcess's neutral-kaon conversion and FillResult's
      // nominal-mass projection, without making G4Tracks or running transport.
      if (std::abs(d.GetPDGcode()) == 311) {
        const int code = G4UniformRand() > 0.5 ? 310 : 130;
        d.SetDefinition(
            G4ParticleTable::GetParticleTable()->FindParticle(code));
      }
      const double nominal = d.GetDefinition()->GetPDGMass();
      if (std::abs(nominal - d.GetMass()) > CLHEP::keV) {
        ++event.offShell;
        d.SetKineticEnergy(
            std::max(d.GetTotalEnergy() - nominal, 0.001 * CLHEP::eV));
        d.SetMass(nominal);
      }
      if (!std::isfinite(d.GetTotalEnergy()) ||
          !std::isfinite(d.GetMomentum().mag2()) || d.GetMass() < 0)
        throw std::runtime_error("nonphysical product");
      G4ThreeVector v = d.GetMomentum();
      v.rotateUz(direction);
      event.products.push_back(
          {d.GetPDGcode(), d.GetMass(), d.GetCharge() / CLHEP::eplus, v});
    };
    if (result->GetStatusChange() != stopAndKill) {
      G4DynamicParticle leading(p, result->GetMomentumChange(),
                                std::max(0., result->GetEnergyChange()));
      add(leading);
    }
    for (size_t j = 0; j < result->GetNumberOfSecondaries(); ++j)
      add(*result->GetSecondary(j)->GetParticle());
    G4LorentzVector sum;
    double q = 0;
    for (auto &d : event.products) {
      sum += G4LorentzVector(d.p, std::hypot(d.p.mag(), d.mass));
      q += d.charge;
    }
    auto initial =
        part.Get4Momentum() + G4LorentzVector(0, 0, 0, event.targetMass);
    // A null interaction omits the unchanged target from its output.
    if (result->GetStatusChange() != stopAndKill &&
        result->GetNumberOfSecondaries() == 0) {
      sum += G4LorentzVector(0, 0, 0, event.targetMass);
      q += event.z;
    }
    event.finalEnergyError = initial.e() - sum.e() - event.edep;
    event.finalMomentumError = (initial.vect() - sum.vect()).mag();
    event.finalChargeError = event.z + part.GetCharge() / CLHEP::eplus - q;
    auto limits = model->GetFatalEnergyCheckLevels();
    event.catastrophic = std::abs(event.finalEnergyError) > limits.second &&
                         std::abs(event.finalEnergyError) > limits.first * ke;
    rng.verify();
    return event;
  }
};
void initialize() {
  G4BosonConstructor().ConstructParticle();
  G4LeptonConstructor().ConstructParticle();
  G4MesonConstructor().ConstructParticle();
  G4BaryonConstructor().ConstructParticle();
  G4IonConstructor().ConstructParticle();
  G4ShortLivedConstructor().ConstructParticle();
  auto *ion = G4GenericIon::Definition();
  ion->SetProcessManager(new G4ProcessManager(ion));
  G4ParticleTable::GetParticleTable()->SetReadiness();
  G4IonTable::GetIonTable()->InitializeLightIons();
  G4PhysicsModelCatalog::Initialize();
  G4HadronicParameters::Instance()->SetVerboseLevel(0);
}
int main(int argc, char **argv) {
  try {
    if (argc < 4)
      throw std::runtime_error("usage: direct-model OUTDIR WORKERS "
                               "EVENTS_PER_POINT [reverse] [SEED_OFFSET]");
    const std::filesystem::path out = argv[1];
    const int nthreads = std::stoi(argv[2]), count = std::stoi(argv[3]);
    const bool reverse = argc > 4 && std::string(argv[4]) == "reverse";
    const long seedOffset = argc > 5 ? std::stol(argv[5]) : 100001;
    if (nthreads < 1 || count < 1 || seedOffset < 1)
      throw std::runtime_error("positive arguments required");
    const size_t total =
        static_cast<size_t>(count) * pdgs.size() * momenta.size();
    std::filesystem::create_directories(out);
    const auto setupStart = std::chrono::steady_clock::now();
    initialize();
    auto *mat = G4NistManager::Instance()->FindOrBuildMaterial("G4_Si");
    Models master; // initialize shared tables before worker creation; no
                   // sampling warm-up
    G4StateManager::GetStateManager()->SetNewState(G4State_Idle);
    std::mutex init;
    std::barrier ready(nthreads + 1), go(nthreads + 1), finish(nthreads + 1),
        cleanup(nthreads + 1);
    std::atomic<size_t> next{0};
    std::vector<std::thread> workers;
    std::vector<std::exception_ptr> errors(nthreads);
    std::vector<Event> results(total);
    for (int t = 0; t < nthreads; ++t)
      workers.emplace_back([&, t] {
        std::unique_ptr<G4ParticlesWorkspace> workspace;
        std::unique_ptr<G4ProcessManager> ionManager;
        std::unique_ptr<Models> models;
        try {
          std::lock_guard lock(
              init); // initialization only; sampling has no application mutex
          G4Threading::G4SetThreadId(t);
          G4ParticleTable::GetParticleTable();
          workspace = std::make_unique<G4ParticlesWorkspace>();
          ionManager =
              std::make_unique<G4ProcessManager>(G4GenericIon::Definition());
          G4GenericIon::Definition()->SetProcessManager(ionManager.get());
          models = std::make_unique<Models>();
          G4StateManager::GetStateManager()->SetNewState(G4State_Idle);
        } catch (...) {
          errors[t] = std::current_exception();
        }
        ready.arrive_and_wait();
        go.arrive_and_wait();
        if (!errors[t])
          try {
            for (;;) {
              const size_t task = next.fetch_add(1, std::memory_order_relaxed);
              if (task >= total)
                break;
              const size_t i = reverse ? total - 1 - task : task;
              results[i] = models->sample(mat, i, seedOffset);
            }
          } catch (...) {
            errors[t] = std::current_exception();
          }
        finish.arrive_and_wait();
        cleanup.arrive_and_wait();
        // Explicit teardown before worker exits. No global registry cleanup on
        // the master.
        models.reset();
        if (ionManager)
          G4GenericIon::Definition()->SetProcessManager(nullptr);
        ionManager.reset();
        if (workspace)
          workspace->DestroyWorkspace();
        G4ParticleTable::GetParticleTable()->DestroyWorkerG4ParticleTable();
      });
    ready.arrive_and_wait();
    const auto start = std::chrono::steady_clock::now();
    const auto cpuStart = std::clock();
    go.arrive_and_wait();
    finish.arrive_and_wait();
    const double cpu = double(std::clock() - cpuStart) / CLOCKS_PER_SEC;
    const double wall =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start)
            .count();
    cleanup.arrive_and_wait();
    for (auto &w : workers)
      w.join();
    for (auto &e : errors)
      if (e)
        std::rethrow_exception(e);
    const double setup =
        std::chrono::duration<double>(start - setupStart).count();
    std::ofstream events(out / "events.csv"), products(out / "products.csv"),
        rates(out / "rates.csv");
    events << std::setprecision(17);
    products << std::setprecision(17);
    rates << std::setprecision(17);
    events
        << "index,pdg,p,hash,rate,A,Z,ftf,status,edep,multiplicity,charged,"
           "leading_fraction,final_energy_error_MeV,final_momentum_error_MeV,"
           "final_charge_error,off_shell,catastrophic\n";
    products << "index,pdg,p,child_pdg,child_mass_MeV,child_charge,px_MeV,py_"
                "MeV,pz_MeV,child_p,cos_theta\n";
    rates << "pdg,p,rate\n";
    size_t calls = 0, catastrophic = 0, offshell = 0;
    for (size_t i = 0; i < total; ++i) {
      const int pdg = pdgs[i % pdgs.size()];
      const double mom = momenta[(i / pdgs.size()) % momenta.size()];
      auto &e = results[i];
      if (i < pdgs.size() * momenta.size())
        rates << pdg << ',' << mom << ',' << e.rate << '\n';
      double leading = 0;
      unsigned mult = 0, charged = 0;
      const auto direction = directionFor(i);
      for (auto &p : e.products) {
        if (std::abs(p.pdg) < 1000000000) {
          ++mult;
          charged += p.charge != 0;
          leading = std::max(leading, std::hypot(p.p.mag(), p.mass));
        }
        products << i << ',' << pdg << ',' << mom << ',' << p.pdg << ','
                 << p.mass << ',' << p.charge << ',' << p.p.x() << ','
                 << p.p.y() << ',' << p.p.z() << ',' << p.p.mag() / CLHEP::GeV
                 << ',' << (p.p.mag() > 0 ? p.p.unit().dot(direction) : 0)
                 << '\n';
      }
      const double mass =
          G4ParticleTable::GetParticleTable()->FindParticle(pdg)->GetPDGMass();
      events << i << ',' << pdg << ',' << mom << ',' << e.hash() << ','
             << e.rate << ',' << e.a << ',' << e.z << ',' << e.ftf << ','
             << e.status << ',' << e.edep << ',' << mult << ',' << charged
             << ',' << leading / std::hypot(mom * CLHEP::GeV, mass) << ','
             << e.finalEnergyError << ',' << e.finalMomentumError << ','
             << e.finalChargeError << ',' << e.offShell << ',' << e.catastrophic
             << '\n';
      calls += e.rate > 0;
      catastrophic += e.catastrophic;
      offshell += e.offShell;
    }
    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    double rss = usage.ru_maxrss;
#ifndef __APPLE__
    rss *= 1024;
#endif
    std::ofstream report(out / "run.json");
    report << std::setprecision(12) << "{\"workers\":" << nthreads
           << ",\"points\":81,\"events_per_point\":" << count
           << ",\"calls\":" << calls << ",\"seed_offset\":" << seedOffset
           << ",\"reverse\":" << (reverse ? "true" : "false")
           << ",\"sampling_wall_s\":" << wall << ",\"sampling_cpu_s\":" << cpu
           << ",\"setup_wall_s\":" << setup
           << ",\"peak_rss_MiB\":" << rss / (1024 * 1024)
           << ",\"catastrophic\":" << catastrophic
           << ",\"off_shell_products\":" << offshell << ",\"geant4_version\":\""
           << G4Version
           << "\",\"caller_rng_preserved\":true,\"run_manager\":false}\n";
    std::cout << "workers=" << nthreads << " calls=" << calls
              << " wall=" << wall << " cpu=" << cpu
              << " catastrophic=" << catastrophic << '\n';
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
