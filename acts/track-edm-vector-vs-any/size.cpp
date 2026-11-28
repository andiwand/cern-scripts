#include "Acts/EventData/FindingTrackContainer.hpp"
#include <iostream>
int main() {
  std::cout << "container " << sizeof(Acts::FindingTrackContainer) << "\ntrack proxy "
            << sizeof(Acts::FindingTrackContainer::TrackProxy) << "\nstate proxy "
            << sizeof(Acts::FindingTrackContainer::TrackStateProxy) << '\n';
}
