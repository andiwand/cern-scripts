"""Build a reviewable dispatch prototype outside the MR candidate."""
from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci')
p=r/'athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool'
o=r/'run/native-pixel-nn/dispatch';(o/'SiClusterizationTool').mkdir(parents=True,exist_ok=True)
h=(p/'SiClusterizationTool/NativePixelClusterNN.h').read_text()
h=h.replace('const std::string& path, unsigned model);','const std::string& path, unsigned model, bool allowAvx2 = true);')
a=h.index('  template <unsigned In, unsigned Out>');b=h.index('  unsigned m_model;',a)
h=h[:a]+'''  void inferSse(std::span<const float> input, std::span<float> output) const;
  void inferAvx2(std::span<const float> input, std::span<float> output) const;

'''+h[b:]
h=h.replace('  unsigned m_model;', '  unsigned m_model;\n  bool m_useAvx2;')
(o/'SiClusterizationTool/NativePixelClusterNN.h').write_text(h)
loader=(p/'src/NativePixelClusterNNFromOnnx.cxx').read_text()
loader=loader.replace('unsigned model) : m_model(model)', 'unsigned model, bool allowAvx2) : m_model(model),\n    m_useAvx2(allowAvx2 && __builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma"))')
assert 'm_useAvx2(allowAvx2' in loader
(o/'Loader.cxx').write_text(loader)
k=(p/'src/NativePixelClusterNN.cxx').read_text()
k=k.replace('#include <Eigen/Core>', '''// Force Eigen helpers into each ISA implementation: do not merge weak
// out-of-line Eigen instantiations compiled with different packet widths.
#define EIGEN_STRONG_INLINE inline __attribute__((always_inline))
#include <Eigen/Core>''')
k=k.replace('}  // namespace\nnamespace InDet {\n\ntemplate <unsigned In, unsigned Out>\nvoid NativePixelClusterNN::dense(const Layer& layer, const float* input, float* output) {', 'template <unsigned In, unsigned Out, class Layer>\nvoid dense(const Layer& layer, const float* input, float* output) {')
k=k.replace('void NativePixelClusterNN::infer(std::span', '}  // namespace\nnamespace InDet {\nvoid NativePixelClusterNN::NATIVE_NN_ENTRY(std::span')
(o/'Kernel.icc').write_text(k)
(o/'Sse.cxx').write_text('#define NATIVE_NN_ENTRY inferSse\n#include "Kernel.icc"\n')
(o/'Avx2.cxx').write_text('#define NATIVE_NN_ENTRY inferAvx2\n#include "Kernel.icc"\n')
(o/'Dispatch.cxx').write_text('''#include "SiClusterizationTool/NativePixelClusterNN.h"
namespace InDet {
void NativePixelClusterNN::infer(std::span<const float> input,
                               std::span<float> output) const {
  if (m_useAvx2) inferAvx2(input, output);
  else inferSse(input, output);
}
}
''')
bench=(Path('/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/bench.cxx')).read_text()
bench=bench.replace('".onnx",i);','".onnx",i,std::getenv("NATIVE_NN_FORCE_SSE")==nullptr);')
assert 'NATIVE_NN_FORCE_SSE' in bench
(o/'bench.cxx').write_text(bench)
