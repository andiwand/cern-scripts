/*
  Copyright (C) 2002-2026 CERN for the benefit of the ATLAS collaboration
*/
#include "SiClusterizationTool/NativePixelClusterNN.h"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#ifdef __SSE2__
#include <emmintrin.h>
#endif

namespace InDet {

template<unsigned In, unsigned Out>
void NativePixelClusterNN::dense(const Layer& layer, const float* input,
                                float* output) {
#ifdef __SSE2__
  if constexpr (Out >= 16) {
    static_assert(Out % 16 == 0);
    for (unsigned i = 0; i < Out; i += 16) {
      __m128 a = _mm_loadu_ps(layer.bias.data() + i);
      __m128 b = _mm_loadu_ps(layer.bias.data() + i + 4);
      __m128 c = _mm_loadu_ps(layer.bias.data() + i + 8);
      __m128 d = _mm_loadu_ps(layer.bias.data() + i + 12);
      for (unsigned j = 0; j < In; ++j) {
        const __m128 x = _mm_set1_ps(input[j]);
        const float* w = layer.weights.data() + j * Out + i;
        a = _mm_add_ps(a, _mm_mul_ps(x, _mm_loadu_ps(w)));
        b = _mm_add_ps(b, _mm_mul_ps(x, _mm_loadu_ps(w + 4)));
        c = _mm_add_ps(c, _mm_mul_ps(x, _mm_loadu_ps(w + 8)));
        d = _mm_add_ps(d, _mm_mul_ps(x, _mm_loadu_ps(w + 12)));
      }
      _mm_storeu_ps(output + i, a);
      _mm_storeu_ps(output + i + 4, b);
      _mm_storeu_ps(output + i + 8, c);
      _mm_storeu_ps(output + i + 12, d);
    }
    return;
  }
#endif
  std::copy_n(layer.bias.data(), Out, output);
  for (unsigned j = 0; j < In; ++j) {
    for (unsigned i = 0; i < Out; ++i) {
      output[i] += input[j] * layer.weights[j * Out + i];
    }
  }
}

void NativePixelClusterNN::infer(std::span<const float> input,
                               std::span<float> output) const {
  if (input.size() != 67 || output.size() != outputSize()) {
    throw std::invalid_argument("NativePixelClusterNN: incorrect input/output size");
  }
  std::array<float, 128> a, b;
  for (unsigned i = 0; i < 67; ++i) {
    a[i] = i < 49 ? input[i] * 1e-5f : input[i];
  }
  const auto silu = [](float* x, unsigned size) {
    for (unsigned i = 0; i < size; ++i) {
      const float e = std::exp(-std::abs(x[i]));
      x[i] *= (x[i] >= 0 ? 1.f : e) / (1.f + e);
    }
  };
  dense<67, 128>(m_layers[0], a.data(), b.data());
  silu(b.data(), 128);
  dense<128, 64>(m_layers[1], b.data(), a.data());
  silu(a.data(), 64);
  dense<64, 32>(m_layers[2], a.data(), b.data());
  silu(b.data(), 32);
  dense<32, 16>(m_layers[3], b.data(), a.data());
  switch (m_model) {
  case 0: dense<16, 3>(m_layers[4], a.data(), output.data()); break;
  case 1: dense<16, 5>(m_layers[4], a.data(), output.data()); break;
  case 2: dense<16, 10>(m_layers[4], a.data(), output.data()); break;
  case 3: dense<16, 15>(m_layers[4], a.data(), output.data()); break;
  }
  const unsigned count = m_model == 0 ? 3 : m_model;
  const unsigned stride = m_model == 0 ? 1 : 5;
  float maximum = output[0];
  for (unsigned i = 1; i < count; ++i) {
    maximum = std::max(maximum, output[stride * i]);
  }
  float sum = 0;
  for (unsigned i = 0; i < count; ++i) {
    output[stride * i] = std::exp(output[stride * i] - maximum);
    sum += output[stride * i];
  }
  for (unsigned i = 0; i < count; ++i) {
    output[stride * i] /= sum;
  }
  for (unsigned i = 0; i < m_model; ++i) {
    for (unsigned k = 3; k < 5; ++k) {
      const float precision = std::abs(output[5 * i + k]) + 1e-4f;
      output[5 * i + k] = precision * precision;
    }
  }
}

} // namespace InDet
