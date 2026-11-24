#!/usr/bin/env python3
from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci')
s=(Path(__file__).parent/'fixtures/BlockedEigenKernel.cxx').read_text()
o=r/'run/native-pixel-nn/optimization';o.mkdir(exist_ok=True)
def silu(text,width):
    start=text.index('    for (unsigned i = 0; i < size; ++i) {',text.index('const auto silu'))
    end=text.index('\n  };',start)
    text=text[:start]+f'''    using Packet = Eigen::Array<float, {width}, 1>;
    for (unsigned i = 0; i < size; i += {width}) {{
      Eigen::Map<Packet> value(x + i);
      const Packet e = (-value.abs()).exp();
      value *= (value >= 0).select(Packet::Ones(), e) / (1.f + e);
    }}'''+text[end:]
    return text
def avx(text):
    a=text.index('      Eigen::Array4f a =')
    b=text.index('\n    }\n    return;',a)
    return text[:a]+'''      using Packet = Eigen::Array<float, 8, 1>;
      Packet a = Eigen::Map<const Packet>(layer.bias.data() + i);
      Packet b = Eigen::Map<const Packet>(layer.bias.data() + i + 8);
      for (unsigned j = 0; j < In; ++j) {
        const float* w = layer.weights.data() + j * Out + i;
        a += input[j] * Eigen::Map<const Packet>(w);
        b += input[j] * Eigen::Map<const Packet>(w + 8);
      }
      Eigen::Map<Packet>{output + i} = a;
      Eigen::Map<Packet>{output + i + 8} = b;'''+text[b:]
start=s.index('  if constexpr (Out >= 16)')
end=s.index('\n}\n\nvoid NativePixelClusterNN::infer',start)
generic=s[:start]+'''  Eigen::Map<Eigen::Matrix<float, Out, 1>> result(output);
  const Eigen::Map<const Eigen::Matrix<float, Out, In>> weights(layer.weights.data());
  result.noalias() = weights * Eigen::Map<const Eigen::Matrix<float, In, 1>>(input);
  result += Eigen::Map<const Eigen::Matrix<float, Out, 1>>(layer.bias.data());'''+s[end:]
for name,code in [('eigen',s),('vector_silu',silu(s,4)),('avx2',avx(s)),('avx2_vector_silu',silu(avx(s),8)),('gemv',generic),('gemv_vector_silu',silu(generic,4))]:
    (o/f'{name}.cxx').write_text(code)
