#!/usr/bin/env python3
"""Generate a compute-only CxxUtils prototype; leave the Athena candidate alone."""
from pathlib import Path

ROOT = Path('/home/astefl/source/acts/acts-athena-ci')
PKG = ROOT / 'athena-native-pixel-nn/InnerDetector/InDetRecTools/SiClusterizationTool'
OUT = ROOT / 'run/native-pixel-nn/cxxutils'
HERE = Path(__file__).resolve().parent
(OUT / 'SiClusterizationTool').mkdir(parents=True, exist_ok=True)

header = (PKG / 'SiClusterizationTool/NativePixelClusterNN.h').read_text()
header = header.replace('const std::string& path, unsigned model);',
                        'const std::string& path, unsigned model, bool allowAvx2 = true);')
begin = header.index('  template <unsigned In, unsigned Out>')
end = header.index('  unsigned m_model;', begin)
header = header[:begin] + '''  void inferSse(std::span<const float>, std::span<float>) const;
  void inferAvx2(std::span<const float>, std::span<float>) const;
''' + header[end:]
header = header.replace('  unsigned m_model;', '  unsigned m_model;\n  bool m_useAvx2;')
(OUT / 'SiClusterizationTool/NativePixelClusterNN.h').write_text(header)

loader = (PKG / 'src/NativePixelClusterNNFromOnnx.cxx').read_text()
loader = loader.replace('unsigned model) : m_model(model)',
    'unsigned model, bool allowAvx2) : m_model(model),\n'
    '    m_useAvx2(allowAvx2 && __builtin_cpu_supports("avx2") && __builtin_cpu_supports("fma"))')
assert 'm_useAvx2(allowAvx2' in loader
(OUT / 'Loader.cxx').write_text(loader)

source = (PKG / 'src/NativePixelClusterNN.cxx').read_text()
activation = source[source.index('template <int N>'):source.index('}  // namespace')]
(OUT / 'Activation.cxx').write_text('#include <Eigen/Core>\nnamespace NativeNNActivation {\n'
    + activation + '\n'.join(f'void silu{n}(float* x) {{ silu<{n}>(x); }}' for n in (128, 64, 32))
    + '\n}\n')
declarations = 'namespace NativeNNActivation {\n' + '\n'.join(
    f'void silu{n}(float*);' for n in (128, 64, 32)) + '\n}\n'

body = source[source.index('void NativePixelClusterNN::infer('):]
body = body.replace('NativePixelClusterNN::infer(', 'NativePixelClusterNN::NN_ENTRY(')
body = body.replace('dense<', 'dense<NN_WIDTH, ')
for n in (128, 64, 32):
    body = body.replace(f'silu<{n}>', f'NativeNNActivation::silu{n}')
prefix = '''#include "SiClusterizationTool/NativePixelClusterNN.h"
#include "CxxUtils/vec.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
'''
(OUT / 'Kernel.icc').write_text(prefix + declarations + (HERE / 'Dense.icc').read_text()
                               + '\nnamespace InDet {\n' + body)
for name, width in [('Sse', 4), ('Avx2', 8)]:
    (OUT / (name + '.cxx')).write_text(
        f'#define NN_WIDTH {width}\n#define NN_ENTRY infer{name}\n#include "Kernel.icc"\n')
(OUT / 'Dispatch.cxx').write_text('''#include "SiClusterizationTool/NativePixelClusterNN.h"
namespace InDet {
void NativePixelClusterNN::infer(std::span<const float> input, std::span<float> output) const {
#ifdef NN_STATIC_SSE
  inferSse(input, output);
#elif defined(NN_STATIC_AVX2)
  inferAvx2(input, output);
#else
  if (m_useAvx2) inferAvx2(input, output);
  else inferSse(input, output);
#endif
}
}
''')
bench = (HERE.parent / 'bench.cxx').read_text()
bench = bench.replace('".onnx",i);', '".onnx",i,std::getenv("NATIVE_NN_FORCE_SSE")==nullptr);')
assert 'NATIVE_NN_FORCE_SSE' in bench
(OUT / 'bench.cxx').write_text(bench)

# Control: original Eigen GEMV, but the same shared SSE activation as CxxUtils.
control = source[:source.index('namespace {')] + declarations + source[source.index('namespace InDet {'):]
control = control.replace('"SiClusterizationTool/NativePixelClusterNN.h"',
                          '<SiClusterizationTool/NativePixelClusterNN.h>')
for n in (128, 64, 32):
    control = control.replace(f'silu<{n}>', f'NativeNNActivation::silu{n}')
(OUT / 'EigenSharedActivation.cxx').write_text(control)
