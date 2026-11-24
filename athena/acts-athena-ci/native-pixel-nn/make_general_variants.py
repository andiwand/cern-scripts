from pathlib import Path
r=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn/optimization')
s=(r/'gemv_vector_silu.cxx').read_text()
a=s.index('  const auto silu =');b=s.index('  dense<67, 128>',a)
s=s[:a]+s[b:]
for size,buffer in [(128,'b'),(64,'a'),(32,'b')]:s=s.replace(f'silu({buffer}.data(), {size});',f'silu<{size}>({buffer}.data());')
s=s.replace('namespace InDet {','''namespace {
template<int N> void silu(float* x) {
  Eigen::Map<Eigen::Array<float, N, 1>> value(x);
  const Eigen::Array<float, N, 1> e = (-value.abs()).exp();
  value *= (value >= 0).select(Eigen::Array<float, N, 1>::Ones(), e) / (1.f + e);
}
}
namespace InDet {''')
for suffix in ['', '_avx2']:(r/f'general_silu{suffix}.cxx').write_text(s)
s=s.replace('Eigen::Map<Eigen::Matrix<float, Out, 1>> result(output);','Eigen::Map<Eigen::VectorXf> result(output, Out);')
s=s.replace('Eigen::Map<const Eigen::Matrix<float, Out, In>> weights(layer.weights.data());','Eigen::Map<const Eigen::MatrixXf> weights(layer.weights.data(), Out, In);')
s=s.replace('Eigen::Map<const Eigen::Matrix<float, In, 1>>(input)','Eigen::Map<const Eigen::VectorXf>(input, In)')
s=s.replace('Eigen::Map<const Eigen::Matrix<float, Out, 1>>(layer.bias.data())','Eigen::Map<const Eigen::VectorXf>(layer.bias.data(), Out)')
for suffix in ['', '_avx2']:(r/f'dynamic_gemv{suffix}.cxx').write_text(s)
p=Path('/home/astefl/scripts/athena/acts-athena-ci/native-pixel-nn/build_more_variants.sh')
x=p.read_text().replace('avx2_four avx2_four_vector_silu gemv_avx2 gemv_avx2_vector_silu;', 'general_silu general_silu_avx2 dynamic_gemv dynamic_gemv_avx2;')
(p.parent/'build_general_variants.sh').write_text(x)
