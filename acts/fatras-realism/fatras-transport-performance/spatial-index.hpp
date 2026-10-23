#pragma once
// External feasibility experiment: immutable geometry, one simulation worker.
// A conservative BVH changes candidate lookup only, not TryAll stepping or
// hits.
#include "Acts/Surfaces/CylinderBounds.hpp"
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
    bool contains(const Box &b) const {
      return (low.array() <= b.low.array()).all() &&
             (high.array() >= b.high.array()).all();
    }
  };

public:
  struct QueryCache {
    const CandidateIndex *owner = nullptr;
    Box region;
    std::vector<std::size_t> nearby;
  };

private:
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
  std::vector<Box> boundsByIndex;
  struct Primitive {
    int type = 0; // 0: unsupported, 1: plane, 2: cylinder
    Acts::Vector3 center = Acts::Vector3::Zero();
    Acts::Vector3 axis = Acts::Vector3::UnitZ();
    double radius = 0;
  };
  std::vector<Primitive> primitives;
  bool pruneFallback;
  std::size_t total = 0;
  void addFallback(const Acts::Vector3 &start, const Acts::Vector3 &end,
                   double tolerance, std::vector<std::size_t> &out) const {
    // Broad phase only. Exact ACTS intersections still decide all hits.
    const double margin =
        tolerance + 64 * std::numeric_limits<double>::epsilon() *
                        std::max({1., start.cwiseAbs().maxCoeff(),
                                  end.cwiseAbs().maxCoeff()});
    for (auto i : fallback) {
      const auto &p = primitives[i];
      if (pruneFallback && p.type == 1) {
        const double a = (start - p.center).dot(p.axis);
        const double b = (end - p.center).dot(p.axis);
        if (std::min(a, b) > margin || std::max(a, b) < -margin)
          continue;
      } else if (pruneFallback && p.type == 2) {
        const Acts::Vector3 a = start - p.center;
        const Acts::Vector3 b = end - p.center;
        const Acts::Vector3 ra = a - a.dot(p.axis) * p.axis;
        const Acts::Vector3 rb = b - b.dot(p.axis) * p.axis;
        const Acts::Vector3 delta = rb - ra;
        const double t =
            delta.squaredNorm() > 0
                ? std::clamp(-ra.dot(delta) / delta.squaredNorm(), 0., 1.)
                : 0.;
        const double minR2 = (ra + t * delta).squaredNorm();
        const double maxR2 = std::max(ra.squaredNorm(), rb.squaredNorm());
        const double lo = std::max(0., p.radius - margin);
        const double hi = p.radius + margin;
        if (maxR2 < lo * lo || minR2 > hi * hi)
          continue;
      }
      out.push_back(i);
    }
  }
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
      const Acts::GeometryContext &gctx, bool prune = false)
      : pruneFallback(prune), total(candidates.size()) {
    boundsByIndex.resize(total);
    primitives.resize(total);
    ++spatialStats.indexes;
    for (std::size_t i = 0; i < candidates.size(); ++i) {
      const auto &c = candidates[i];
      const auto &s = *c.representation;
      const auto type = s.bounds().type();
      const auto &tr = s.localToGlobalTransform(gctx);
      auto &primitive = primitives[i];
      primitive.center = tr.translation();
      primitive.axis = tr.rotation().col(2);
      if (s.type() == Acts::Surface::Plane || s.type() == Acts::Surface::Disc)
        primitive.type = 1;
      else if (s.type() == Acts::Surface::Cylinder &&
               type == Acts::SurfaceBounds::eCylinder) {
        primitive.type = 2;
        primitive.radius = static_cast<const Acts::CylinderBounds &>(s.bounds())
                               .get(Acts::CylinderBounds::eR);
      }
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
      boundsByIndex[i] = box;
    }
    if (!items.empty())
      build(0, items.size());
  }
  void candidates(const Acts::Vector3 &position, const Acts::Vector3 &direction,
                  double near, double far, double tolerance,
                  std::vector<std::size_t> &out) const {
    ++spatialStats.queries;
    spatialStats.available += total;
    out.clear();
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
      addFallback(position + near * direction, position + far * direction,
                  tolerance, out);
      if (!items.empty())
        query(0, segment, out);
      // Keep original candidate order, including equal-distance intersections.
      std::sort(out.begin(), out.end());
    }
    spatialStats.tested += out.size();
    return;
  }
  // Cache only a conservative spatial superset. Every query still filters by
  // its exact segment box, preserves candidate order and runs exact ACTS
  // intersections. Thus curvature, scattering and backward steps need no
  // special invalidation; a volume change changes the owner.
  void candidates(const Acts::Vector3 &position, const Acts::Vector3 &direction,
                  double near, double far, double tolerance,
                  std::vector<std::size_t> &out, QueryCache &cache) const {
    if (!std::isfinite(near) || !std::isfinite(far) || std::abs(far) > 1e10) {
      candidates(position, direction, near, far, tolerance, out);
      return;
    }
    ++spatialStats.queries;
    spatialStats.available += total;
    Box segment;
    segment.add(position + near * direction);
    segment.add(position + far * direction);
    segment.low.array() -= tolerance;
    segment.high.array() += tolerance;
    if (cache.owner != this || !cache.region.contains(segment)) {
      cache.owner = this;
      cache.region = segment;
      cache.region.low.array() -= 10.;
      cache.region.high.array() += 10.;
      cache.nearby.clear();
      if (!items.empty())
        query(0, cache.region, cache.nearby);
    }
    out.clear();
    addFallback(position + near * direction, position + far * direction,
                tolerance, out);
    for (auto index : cache.nearby)
      if (boundsByIndex[index].overlaps(segment))
        out.push_back(index);
    std::sort(out.begin(), out.end());
    spatialStats.tested += out.size();
  }
};
