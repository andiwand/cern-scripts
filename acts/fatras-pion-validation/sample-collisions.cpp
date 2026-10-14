// Conditional Si-library prediction at the measured G4 collision kinematics.
#include "ActsFatras/Physics/Hadronic/NuclearInteractionTable.hpp"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <random>
#include <sstream>
void sample(const ActsFatras::NuclearInteractionTable &table,
            const std::string &input, const std::string &outputPath, int trials,
            unsigned seed) {
  std::ifstream records(input);
  std::ofstream output(outputPath);
  if (trials < 1 || !records || !output)
    throw std::runtime_error("invalid input/output");
  std::mt19937_64 rng(seed);
  std::uniform_real_distribution<double> uniform(0, 1);
  output << std::setprecision(12)
         << "row,supported,mean_charged,mean_accepted,variance_accepted,mean_"
            "accepted_pt_sum,mean_accepted_angle_sum\n";
  std::string line;
  std::getline(records, line);
  std::size_t row = 0;
  while (std::getline(records, line)) {
    std::vector<std::string> cells;
    std::istringstream stream(line);
    std::string cell;
    while (std::getline(stream, cell, ','))
      cells.push_back(cell);
    const auto pdg = static_cast<Acts::PdgParticle>(std::stoi(cells.at(5)));
    const double p = std::stod(cells.at(8));
    const auto *channel = table.findReferenceChannel(pdg);
    const auto *bin = channel ? table.findBin(*channel, p) : nullptr;
    if (!bin || bin->events.empty() || std::stoi(cells.at(7)) != 121) {
      output << row++ << ",0,0,0,0,0,0\n";
      continue;
    }
    ActsFatras::Particle parent(ActsFatras::Barcode().withParticle(1), pdg);
    parent.setAbsoluteMomentum(p).setDirection(std::stod(cells.at(10)),
                                               std::stod(cells.at(11)),
                                               std::stod(cells.at(12)));
    std::uniform_int_distribution<std::size_t> choose(0,
                                                      bin->events.size() - 1);
    double charged = 0, accepted = 0, accepted2 = 0, ptsum = 0, anglesum = 0;
    for (int i = 0; i < trials; ++i) {
      const auto &event = bin->events[choose(rng)];
      const auto sample =
          table.sample(event, parent, 2 * std::numbers::pi * uniform(rng));
      int count = 0;
      for (const auto &product : sample.products) {
        if (product.charge == 0)
          continue;
        ++charged;
        double pm = product.momentum.norm(),
               pt = product.momentum.head<2>().norm();
        if (pm >= .1 && pt >= .05) {
          ++count;
          ptsum += pt;
          anglesum += std::acos(std::clamp(
              product.momentum.dot(parent.direction()) / pm, -1., 1.));
        }
      }
      accepted += count;
      accepted2 += count * count;
    }
    output << row++ << ",1," << charged / trials << ',' << accepted / trials
           << ',' << accepted2 / trials - std::pow(accepted / trials, 2) << ','
           << ptsum / trials << ',' << anglesum / trials << '\n';
  }
}
int main(int argc, char **argv) {
  try {
    if (argc != 6)
      return 2;
    std::ifstream file(argv[1]);
    auto table = ActsFatras::NuclearInteractionTable::read(file);
    const int events = std::stoi(argv[4]), trials = std::stoi(argv[5]);
    for (int event = 0; event < events; ++event) {
      std::ostringstream stem;
      stem << "event" << std::setfill('0') << std::setw(9) << event;
      sample(
          table,
          (std::filesystem::path(argv[2]) /
           (stem.str() + "-pion_interactions.csv"))
              .string(),
          (std::filesystem::path(argv[3]) / (stem.str() + "-conditional.csv"))
              .string(),
          trials, 19348 + event);
      std::cout << event << " sampled" << std::endl;
    }
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
