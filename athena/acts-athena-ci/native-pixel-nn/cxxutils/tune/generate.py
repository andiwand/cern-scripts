#!/usr/bin/env python3
"""Activation and small-head experiments, isolated from the first prototype."""
from pathlib import Path
import shutil

ROOT = Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/cxxutils')
OUT = ROOT / 'tuning'
HERE = Path(__file__).resolve().parent
(OUT / 'SiClusterizationTool').mkdir(parents=True, exist_ok=True)
for name in ['SiClusterizationTool/NativePixelClusterNN.h', 'Sse.cxx', 'Avx2.cxx']:
    shutil.copyfile(ROOT / name, OUT / name)
kernel = (ROOT / 'Kernel.icc').read_text()
begin = kernel.index('namespace NativeNNActivation {')
end = kernel.index('// Prototype:', begin)
kernel = kernel[:begin] + '#include <Eigen/Core>\n' + (HERE / 'Activation.icc').read_text() + kernel[end:]
for n in [128, 64, 32]:
    kernel = kernel.replace(f'NativeNNActivation::silu{n}', f'packetSilu<NN_WIDTH, {n}>')
kernel = kernel.replace('void NativePixelClusterNN::NN_ENTRY(',
    '#ifdef NN_FLATTEN_PACKET\nATH_FLATTEN\n#endif\nvoid NativePixelClusterNN::NN_ENTRY(')
kernel = kernel.replace('      Vector sums[Blocks]{};', '''      Vector sums[Blocks]{};
#ifdef NN_BIAS_FIRST
#pragma GCC unroll 8
      for (unsigned k = 0; k < Blocks; ++k)
        CxxUtils::vload(sums[k], layer.bias.data() + i + k * Width);
#endif''')
kernel = kernel.replace('''        Vector bias;
        CxxUtils::vload(bias, layer.bias.data() + i + k * Width);
        CxxUtils::vstore(output + i + k * Width, sums[k] + bias);''', '''#ifdef NN_BIAS_FIRST
        CxxUtils::vstore(output + i + k * Width, sums[k]);
#else
        Vector bias;
        CxxUtils::vload(bias, layer.bias.data() + i + k * Width);
        CxxUtils::vstore(output + i + k * Width, sums[k] + bias);
#endif''')
before = '''    std::fill_n(output, Out, 0.f);
    for (unsigned j = 0; j < In; ++j) {
      for (unsigned i = 0; i < Out; ++i) {
        output[i] += layer.weights[j * Out + i] * input[j];
      }
    }
    for (unsigned i = 0; i < Out; ++i) output[i] += layer.bias[i];'''
assert before in kernel
after = '''#ifdef NN_LOCAL_HEADS
    std::array<float, Out> sums{};
    for (unsigned j = 0; j < In; ++j) {
#pragma GCC unroll 16
      for (unsigned i = 0; i < Out; ++i)
        sums[i] += layer.weights[j * Out + i] * input[j];
    }
    for (unsigned i = 0; i < Out; ++i) output[i] = sums[i] + layer.bias[i];
#else
''' + before + '\n#endif'
kernel = kernel.replace(before, after)
(OUT / 'Kernel.icc').write_text(kernel)
