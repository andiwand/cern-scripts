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
python run.py results                # 10k muons at 1, 10 and 100 GeV, 4 variants
python plot.py results               # -> results/seed_parameter_resolution.pdf
```

`run.py` writes `performance_<variant>_pt<pt>.root` per point, each a
`RootTrackParameterPerformanceWriter` output. `plot.py` reads the
`reswidth_<param>_vs_eta` profiles the writer fits on the way out;
`--estimator quantile` swaps in the half width of the central 68.27% interval
of the raw residual histogram as a cross-check.

Every point runs twice. A short calibration pass on wide asinh axes measures
the residual widths, then the production pass puts regular axes around them at
`--residual-range-sigmas` times the 90th percentile over eta. This is not
optional: the widths span more than an order of magnitude between the variants,
so fixed axes either clip the wide ones or leave the narrow ones a few bins,
and the writer's Gaussian core fit needs both the core resolved and the axis
untruncated. Variable bin widths do not work either - the fit is on bin
contents, not a density, so a wide tail bin reads as extra population and
drags the fitted sigma up by a factor of a few.

## Findings

Resolution averaged over `|eta| < 1`:

| pT [GeV] | variant | d0 [um] | z0 [um] | q/pT [%] |
|---:|---|---:|---:|---:|
| 1 | truth_all | 55 | 69 | 3.3 |
| 1 | truth_spread3 | 60 | 93 | 3.4 |
| 1 | truth_inner3 | 68 | 72 | 5.7 |
| 1 | triplet | 73 | 101 | 4.4 |
| 10 | truth_all | 30 | 20 | 11.4 |
| 10 | truth_spread3 | 32 | 21 | 13.4 |
| 10 | truth_inner3 | 53 | 22 | 37.5 |
| 10 | triplet | 47 | 24 | 20.2 |
| 100 | truth_all | 29 | 18 | 106 |
| 100 | truth_spread3 | 31 | 19 | 131 |
| 100 | truth_inner3 | 53 | 21 | 379 |
| 100 | triplet | 48 | 21 | 213 |

- At 1 GeV multiple scattering swamps the geometry and all four variants land
  within 30% of each other. The lever arm only starts to pay at 10 GeV and
  above, where the ordering is all > spread > triplet > innermost throughout.
- Fitting every space point buys little over three well spread ones: 5-10% in
  d0 and z0, ~15% in q/pT. Almost all of the gain is in the spread, not in the
  number of points. Reaching the outermost pixel layer is what matters.
- q/pT from a pixel-only seed is not a momentum measurement above ~10 GeV. At
  100 GeV the sagitta over the pixel lever arm is comparable to the hit
  resolution, and even the best variant is 100% wrong. Whatever consumes a seed
  estimate has to treat q/pT as an order of magnitude, not a value.
- Triplet seeding sits between `truth_spread3` and `truth_inner3`, which is
  what its deltaR cuts select. It also produces ~7 seeds per muon, all of which
  enter the histograms - the truth variants contribute one each. That is the
  population a CKF actually starts from, but it is not a like-for-like
  comparison of one estimate per track; the last PDF page shows the counts.
- z0 is flat across the variants except at 1 GeV. It is set by the innermost
  space point and the theta estimate, and none of the variants moves either.

## Caveats

- Pixel space points only (`odd-seeding-config.json`), so "outermost layer"
  means the fourth pixel barrel layer, not the strips. Including strips would
  change the lever-arm conclusions.
- Muons need 9 measurements to enter, the ODD standard cut, so all variants see
  the same particles.
- The seed covariances are inflated by `TrackParamsEstimationAlgorithm`, so the
  pulls in the ROOT files are far below one by construction and are not plotted.
