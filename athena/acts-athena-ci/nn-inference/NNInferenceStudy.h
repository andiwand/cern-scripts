#pragma once
#include <array>
#include <chrono>
#include <cstdint>
#include <memory>
#include <string>

namespace nnstudy {
class Engine {
 public:
  explicit Engine(const std::string& backend, const std::string& directory);
  ~Engine();
  void infer(unsigned model, const float* input, float* output);
 private:
  struct Impl;
  std::unique_ptr<Impl> m_impl;
};
// Private study hooks: backend is fixed for the process, scratch is per thread.
bool replacementEnabled();
void infer(unsigned model, const float* input, float* output);
void capture(const float* input);
bool profilingEnabled();
void recordProfile(unsigned stage, std::uint64_t nanoseconds);
class CalibrationProfile {
  using Clock = std::chrono::steady_clock;
  bool m_active = profilingEnabled();
  Clock::time_point m_last;
 public:
  CalibrationProfile() { if (m_active) m_last = Clock::now(); }
  void mark(unsigned stage) {
    if (!m_active) return;
    const auto now = Clock::now();
    recordProfile(stage, std::chrono::duration_cast<std::chrono::nanoseconds>(now-m_last).count());
    m_last = Clock::now();
  }
  ~CalibrationProfile() { mark(3); }
};
}
