#!/usr/bin/env python3
"""Install private backend hooks in the isolated Athena study worktree."""
from pathlib import Path
root=Path('/home/astefl/source/acts/acts-athena-ci')
pkg=root/'athena-nn-inference/Tracking/Acts/ActsTrackReconstruction'
scripts=Path(__file__).resolve().parent
p=pkg/'src/detail/NNClusterCalibratorToolImpl.icc'
s=p.read_text()
assert 'NNInferenceStudy' not in s
s=s.replace('#include "NNPixelClusterCalibratorHelpers.h"','#include "NNPixelClusterCalibratorHelpers.h"\n#include "NNInferenceStudy.h"')
s=s.replace('  // 1st call to\n  std::array<float, 3> probabilities = NNPixelCluster::predictNumberOfClusters(\n      *m_options.m_models->numberNetwork, nnInput);','''  nnstudy::capture(nnInput.payload().data());
  std::array<float, 3> probabilities;
  if (nnstudy::replacementEnabled()) {
    nnstudy::infer(0, nnInput.payload().data(), probabilities.data());
  } else {
    probabilities = NNPixelCluster::predictNumberOfClusters(
        *m_options.m_models->numberNetwork, nnInput);
  }''')
needle='  Ort::Session& session = selectPositionNetwork(number);'
assert needle in s
s=s.replace(needle,'''  if (nnstudy::replacementEnabled()) {
    std::array<float, 15> result{};
    nnstudy::infer(number, nn.payload().data(), result.data());
    return PositionNNoutput(result.data(), result.data() + 5 * number);
  }
'''+needle)
s=s.replace('  ActsTrk::NNinput nnInput;', '  nnstudy::CalibrationProfile profile;\n  ActsTrk::NNinput nnInput;')
s=s.replace('  nnstudy::capture(', '  profile.mark(0);\n  nnstudy::capture(')
s=s.replace('  // pick max probability', '  profile.mark(1);\n  // pick max probability')
s=s.replace('      predictPositions(nnInput, maxProbNumberOfClusters);', '      predictPositions(nnInput, maxProbNumberOfClusters);\n  profile.mark(2);')
p.write_text(s)
p=pkg/'CMakeLists.txt';s=p.read_text()
s=s.replace('INCLUDE_DIRS ${Boost_INCLUDE_DIRS}',f'INCLUDE_DIRS ${{Boost_INCLUDE_DIRS}} {scripts}')
s=s.replace('LINK_LIBRARIES ${Boost_LIBRARIES}',f'LINK_LIBRARIES ${{Boost_LIBRARIES}} {root}/run/nn-inference/build/libNNInferenceStudy.so')
p.write_text(s)
print('Installed isolated study hooks')
