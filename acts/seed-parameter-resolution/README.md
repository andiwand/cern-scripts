# Seed parameter resolution

How well the track parameters estimated from a seed describe the track, as a
function of which space points go into the estimate. Single muons at fixed pT
with flat eta in the ODD pixels, Fatras, seeds extrapolated to a perigee at the
origin so every variant is compared to truth on the same surface.

## Variants

| name | seeding | space points | estimator |
|---|---|---|---|
| `truth_all` | truth | every pixel space point on the track | least-squares helix over all of them |
| `truth_inner3` | truth | the three innermost layers | exact helix through three points |
| `truth_spread3` | truth | innermost, middle and outermost layer | exact helix through three points |
| `triplet` | grid triplet | whatever the seeder found | exact helix through three points |

The triplet selections pick one space point per *layer*. Neighbouring modules
of an ODD pixel layer overlap, so a track can leave two space points at nearly
the same radius; a triplet holding both is close to degenerate and gives a
bimodal residual - a narrow core plus a component an order of magnitude wider.
Selecting by space point rather than by layer costs `truth_inner3` a factor 8
in d0 and a factor 16 in q/pT.

## Running

```sh
python run.py results                # 100k muons at 1, 10 and 100 GeV, 4 variants
python plot.py results               # -> results/seed_parameter_resolution.pdf
```

1.2M muons in under two minutes on 12 cores. The event loop is threaded
(`--threads`, all cores by default) but only reaches ~300% CPU: a single-muon
event is small enough that the serial parts, the writer's fill mutex above all,
set the pace. Shorter runs scale worse still, since the ~2 s of ODD geometry
building is paid per point.

`run.py` writes `performance_<variant>_pt<pt>.root` per point, each a
`RootTrackParameterPerformanceWriter` output. `plot.py` reads the
`reswidth_<param>_vs_eta` profiles the writer fits on the way out;
`--estimator quantile` swaps in the half width of the central 68.27% interval
of the raw residual histogram as a cross-check.

One page per pT with the variants overlaid: resolution, the ratio to
`--reference` (`truth_all` by default, its own error drawn as the band at one),
and the bias. The ratio panels are scaled to the bulk of their points, and what
runs off the top is flagged with a triangle at the edge rather than dropped.
Since all variants run over the same muons their fluctuations partly cancel, so
the ratio errors, added in quadrature, are conservative.

Every point runs twice. A short calibration pass on wide asinh axes measures
the 68% width of every residual in every eta bin, and the production pass puts
a regular axis around them: `--residual-range-sigmas` times the 90th percentile
over eta sets the half range, the 10th percentile over `--bins-per-sigma` sets
the bin width, and `--residual-bins` clamps the count that falls out, which
lands between 100 and 950 depending on the parameter.

Both ends have to come from the data because both bite. Toys through the same
iterative +-3 sigma fit put it within a percent of the truth between 2 and 10
bins per sigma; below that it reads the bin width instead of the core, +4% at
one bin per sigma and +8% at 0.7, and above ~20 it drifts 2 to 3% low as the
chi square starts to see sparse bins. A fixed 200 bins left the 1 GeV triplet
z0 core 0.9 bins wide at eta 0 and 18 at eta 3: the barrel came out 6% high on
average and 10% at eta 0, and the eta dependence flattened with it. The same
axis gave d0 15 bins per sigma, which cost a percent the other way.

`--calibration-events` has to keep every eta bin above
`--calibration-min-entries`, which is why it is 5000 and not the 1000 that
looks like plenty for measuring a width. At 1000, three or four of the 24 eta
bins of a one-seed-per-muon variant survived the cut, and they were wherever
the Poisson fluctuations fell rather than the wide forward ones, so the range
came out up to a factor three short and the forward z0 residuals were truncated
by their own axis - 12% at eta 3 for `truth_inner3` at 100 GeV.

Variable bin widths would sidestep the tension between the two ends, but the
fit is on bin contents rather than a density, so a wide tail bin reads as extra
population: on the calibration axes the same fit comes out 14% to 64% high, or
43% low, depending on where the core falls. So the tension stays, and `run.py`
warns about any point whose axis cannot serve every eta bin. z0 always trips
it. Its width spans a factor 20 over eta, so bins fine enough for the barrel
leave the forward bins at 50 to 100 per sigma and a couple of percent low.
That is the better end to lose, and the quantile estimator does not have the
problem at either end.

## Findings

Resolution averaged over `|eta| < 1`, 100k muons per point, with the ratio to
`truth_all` in brackets:

| pT [GeV] | variant | d0 [um] | z0 [um] | q/pT [%] |
|---:|---|---:|---:|---:|
| 1 | truth_all | 56 | 69 | 3.5 |
| 1 | truth_spread3 | 61 (1.08) | 92 (1.33) | 3.6 (1.03) |
| 1 | truth_inner3 | 69 (1.24) | 73 (1.05) | 6.0 (1.70) |
| 1 | triplet | 74 (1.32) | 95 (1.37) | 4.4 (1.25) |
| 10 | truth_all | 30 | 19 | 11.5 |
| 10 | truth_spread3 | 32 (1.05) | 21 (1.12) | 13.7 (1.18) |
| 10 | truth_inner3 | 52 (1.71) | 22 (1.16) | 36.9 (3.20) |
| 10 | triplet | 48 (1.58) | 23 (1.23) | 20.8 (1.80) |
| 100 | truth_all | 30 | 18 | 110 |
| 100 | truth_spread3 | 32 (1.05) | 19 (1.09) | 133 (1.21) |
| 100 | truth_inner3 | 52 (1.72) | 21 (1.18) | 366 (3.33) |
| 100 | triplet | 50 (1.68) | 21 (1.17) | 218 (1.99) |

- At 1 GeV multiple scattering compresses the differences to 5-37%, and in
  q/pT the three spread points already match the all-points fit exactly. The
  lever arm only pays from 10 GeV up, where the ordering is all > spread >
  triplet > innermost in d0 and q/pT.
- Fitting every space point buys little over three well spread ones: 5% in d0,
  9-12% in z0, 18-21% in q/pT above 1 GeV. Almost all of the gain is in the
  spread, not in the number of points. Reaching the outermost pixel layer is
  what matters.
- q/pT from a pixel-only seed is not a momentum measurement above ~10 GeV. At
  100 GeV the sagitta over the pixel lever arm is comparable to the hit
  resolution, and even the best variant is 100% wrong. Whatever consumes a seed
  estimate has to treat q/pT as an order of magnitude, not a value.
- Triplet seeding sits between `truth_spread3` and `truth_inner3`, which is
  what its deltaR cuts select. It also produces ~7 seeds per muon, all of which
  enter the histograms - the truth variants contribute one each. That is the
  population a CKF actually starts from, but it is not a like-for-like
  comparison of one estimate per track; the last PDF page shows the counts.
- z0 inverts the ordering at 1 GeV, which the ratio panel shows and the log
  axis hides: `truth_inner3` is within 5% of the all-points reference while
  `truth_spread3` is 33% and `triplet` 37% worse - the reverse of their d0 and
  q/pT ranking. Reaching for the outer layers costs z0 there, because the
  scattering picked up on the way out is extrapolated back to the beam line.
  Above 10 GeV the effect is gone and all variants agree to 23%.

## Caveats

- Pixel space points only (`odd-seeding-config.json`), so "outermost layer"
  means the fourth pixel barrel layer, not the strips. Including strips would
  change the lever-arm conclusions.
- Muons need 9 measurements to enter, the ODD standard cut, so all variants see
  the same particles.
- The seed covariances are inflated by `TrackParamsEstimationAlgorithm`, so the
  pulls in the ROOT files are far below one by construction and are not plotted.
