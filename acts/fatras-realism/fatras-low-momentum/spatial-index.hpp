#pragma once
// External feasibility experiment: immutable geometry, one simulation worker.
// A conservative BVH changes candidate lookup only, not TryAll stepping or
// hits.
#include "Acts/Surfaces/PlanarBounds.hpp"
#include "Acts/Surfaces/PlaneSurface.hpp"
#include "Acts/Surfaces/RectangleBounds.hpp"
#include <numeric>
#include <unordered_map>

struct SpatialStats {
  std::uint64_t queries = 0, available = 0, tested = 0, nodes = 0, indexes = 0;
};
inline SpatialStats spatialStats;

class CandidateIndex {
  struct Box {
    Acts::Vector3 low =
        Acts::Vector3::Constant(std::numeric_limits<double>::infinity());
    Acts::Vector3 high = -low;
    void add(const Acts::Vector3 &p) {
      low = low.cwiseMin(p);
      high = high.cwiseMax(p);
    }
    void add(const Box &b) {
      add(b.low);
      add(b.high);
    }
    bool overlaps(const Box &b) const {
      return (low.array() <= b.high.array()).all() &&
             (high.array() >= b.low.array()).all();
    }
  };
  struct Item {
    Box bounds;
    std::size_t index;
  };
  struct Node {
    Box bounds;
    std::size_t begin = 0, end = 0, left = 0, right = 0;
  };
  std::vector<Item> items;
  std::vector<Node> nodes;
  std::vector<std::size_t> fallback;
  std::size_t total = 0;
  std::size_t build(std::size_t begin, std::size_t end) {
    const auto id = nodes.size();
    nodes.emplace_back();
    Box bounds;
    for (auto i = begin; i < end; ++i)
      bounds.add(items[i].bounds);
    nodes[id].bounds = bounds;
    nodes[id].begin = begin;
    nodes[id].end = end;
    if (end - begin > 8) {
      Eigen::Index axis;
      (bounds.high - bounds.low).maxCoeff(&axis);
      const auto middle = (begin + end) / 2;
      std::nth_element(items.begin() + begin, items.begin() + middle,
                       items.begin() + end,
                       [axis](const auto &a, const auto &b) {
                         return a.bounds.low[axis] + a.bounds.high[axis] <
                                b.bounds.low[axis] + b.bounds.high[axis];
                       });
      const auto left = build(begin, middle), right = build(middle, end);
      nodes[id].left = left;
      nodes[id].right = right;
    }
    return id;
  }
  void query(std::size_t id, const Box &box,
             std::vector<std::size_t> &out) const {
    ++spatialStats.nodes;
    const auto &node = nodes[id];
    if (!node.bounds.overlaps(box))
      return;
    if (node.left != 0) {
      query(node.left, box, out);
      query(node.right, box, out);
      return;
    }
    for (auto i = node.begin; i < node.end; ++i)
      if (items[i].bounds.overlaps(box))
        out.push_back(items[i].index);
  }

public:
  CandidateIndex(
      const std::vector<Acts::detail::NavigationObjectCandidate> &candidates,
      const Acts::GeometryContext &gctx)
      : total(candidates.size()) {
    ++spatialStats.indexes;
    for (std::size_t i = 0; i < candidates.size(); ++i) {
      const auto &c = candidates[i];
      const auto &s = *c.representation;
      const auto type = s.bounds().type();
      // The external macOS bridge has hidden RTTI. Use ACTS's bounds tag for
      // its known rectangle/trapezoid classes; keep every other type unpruned.
      const bool supported = type == Acts::SurfaceBounds::eRectangle ||
                             type == Acts::SurfaceBounds::eTrapezoid;
      // Every unsupported surface/tolerance remains in the exact search.
      if (s.type() != Acts::Surface::Plane || !supported ||
          !c.boundaryTolerance.isNone()) {
        fallback.push_back(i);
        continue;
      }
      Box box;
      // Use boundingBox rather than tessellated vertices: curved planar bounds
      // must also be enclosed conservatively after rotation.
      for (const auto &v : static_cast<const Acts::PlanarBounds &>(s.bounds())
                               .boundingBox()
                               .vertices())
        box.add(s.localToGlobalTransform(gctx) *
                Acts::Vector3(v.x(), v.y(), 0));
      items.push_back({box, i});
    }
    if (!items.empty())
      build(0, items.size());
  }
  std::vector<std::size_t> candidates(const Acts::Vector3 &position,
                                      const Acts::Vector3 &direction,
                                      double near, double far,
                                      double tolerance) const {
    ++spatialStats.queries;
    spatialStats.available += total;
    std::vector<std::size_t> out;
    if (!std::isfinite(near) || !std::isfinite(far) || std::abs(far) > 1e10) {
      out.resize(total);
      std::iota(out.begin(), out.end(), 0);
    } else {
      Box segment;
      segment.add(position + near * direction);
      segment.add(position + far * direction);
      // Include numerical on-surface classification at segment endpoints.
      segment.low.array() -= tolerance;
      segment.high.array() += tolerance;
      out = fallback;
      if (!items.empty())
        query(0, segment, out);
      // Keep original candidate order, including equal-distance intersections.
      std::sort(out.begin(), out.end());
    }
    spatialStats.tested += out.size();
    return out;
  }
};
