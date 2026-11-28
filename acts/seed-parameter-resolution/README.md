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
| `truth_all_refine10` | truth | every pixel space point on the track | as `truth_all`, plus 10 Gauss-Newton iterations on the circle |
| `truth_all_invr2` | truth | every pixel space point on the track | as `truth_all`, points weighted by 1/r^2 |

The triplet selections pick one space point per *layer*. Neighbouring modules
of an ODD pixel layer overlap, so a track can leave two space points at nearly
the same radius; a triplet holding both is close to degenerate and gives a
bimodal residual - a narrow core plus a component an order of magnitude wider.
Selecting by space point rather than by layer costs `truth_inner3` a factor 8
in d0 and a factor 16 in q/pT.

## Running

```sh
out=~/cern/data/seed-parameter-resolution/results
python run.py $out                   # 100k muons at 1, 10 and 100 GeV, 6 variants
python plot.py $out                  # -> $out/seed_parameter_resolution.pdf
```

1.8M muons in two and a half minutes on 12 cores. The event loop is threaded
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

## Caveats

- Pixel space points only (`odd-seeding-config.json`), so "outermost layer"
  means the fourth pixel barrel layer, not the strips.
- Muons need 9 measurements to enter, the ODD standard cut, so all variants see
  the same particles.
- The seed covariances are inflated by `TrackParamsEstimationAlgorithm`, so the
  pulls in the ROOT files are far below one by construction and are not plotted.
