// Study adapter to the unchanged, validated native pixel NN implementation.
#pragma once
#include "SiClusterizationTool/NativePixelClusterNN.h"
#include <onnxruntime_cxx_api.h>
#include <cstdlib>
#include <memory>

namespace tailScoreStudy {
inline void infer(unsigned head, std::span<const float> input, std::span<float> output) {
  struct Models {
    Ort::Env env{ORT_LOGGING_LEVEL_WARNING, "tail-score-native"};
    std::array<std::unique_ptr<const InDet::NativePixelClusterNN>, 4> networks;
    Models() {
      const char* directory = std::getenv("TAIL_SCORE_NATIVE_MODELS");
      if (!directory) throw std::runtime_error("TAIL_SCORE_NATIVE_MODELS is required");
      for (unsigned i = 0; i < networks.size(); ++i) {
        const auto name = i == 0 ? "number" : "pos" + std::to_string(i);
        networks[i] = std::make_unique<const InDet::NativePixelClusterNN>(
            env, std::string(directory) + "/" + name + ".onnx",
            static_cast<InDet::IPixelClusterNN::Model>(i));
      }
    }
  };
  static const Models models;
  models.networks.at(head)->infer(input, output);
}
}
