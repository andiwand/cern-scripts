#!/usr/bin/env python3
"""Fill the sections of the stay-on-seed note."""
import os
N = os.path.expanduser("~/notes/atlas/tsi/notebook/2026-11-11_stay-on-seed-gbts.md")
s = open(N).read()
R = {}
R["SUMMARY"] = """- **Forcing still helps, by a small amount.** It gains 0.2% efficiency (HS and PU) at equal fakes, with slightly more duplicates (436 vs 415), and saves 2.4% of track-finding CPU.
- **It compensates for a poor start direction.** The first/middle/last estimate carries normal core multiple scattering, and the greedy CKF then takes a wrong neighbouring hit at SP1/SP2. Hard scatters are a small part.
- **The seeder does not need to do the finding.** A helix fit of all space points with the outer ones down-weighted, without forcing, reaches 86.72% / 82.74% (forcing on: 86.83% / 82.75%) for about 4.9% more CPU than today. Forcing plus the fit is the best result: 86.86% / 82.86% at +2.0% CPU.
- **The very local estimate fails on the transverse lever arm** in the forward region. A threshold on the transverse gap repairs it, but it does not beat the fit.
- **The fit itself is cheap**, about 1 µs per seed. There is some room left in the eigensolver and `std::pow`.
- **GBTS seeds are mostly clean.** Pixel seeds are 93.8% pure; wrong space points are single (97%), at the front in the barrel and at the back at |η| 2.5–3.5.
- **Inward-first search does not remove the need for forcing.** It matches forward up to |η| 2.5 once the second pass has a stopper, but loses 8% at |η| ≥ 2.5 and triples the duplicates."""
R["VARTABLE"] = """| variant | tracks | eff HS | eff PU | fakes | dupl. | PU gained / lost vs forcing on |
|---|---|---|---|---|---|---|
| forcing on (main) | 663332 | 86.83% | 82.75% | 3.04% | 436 | |
| forcing off | 661409 | 86.61% | 82.55% | 3.02% | 415 | +104 / −863 |
| off, first three SPs (mode 0) | 657350 | 86.32% | 82.20% | 2.95% | 375 | +1051 / −3151 |
| off, first three SPs, q/p from first/middle/last (mode 1) | 660086 | 86.59% | 82.58% | 2.96% | 384 | +937 / −1608 |
| off, as mode 1 with transverse gap ≥ 30 mm | 662247 | 86.65% | 82.68% | 3.01% | 413 | +678 / −962 |
| off, as mode 1 with transverse gap ≥ 60 mm | 661953 | 86.67% | 82.65% | 3.01% | 412 | +588 / −963 |
| off, fit all SPs, uniform (mode 4) | 662207 | 86.71% | 82.63% | 3.02% | 413 | +475 / −947 |
| **off, fit all SPs, 1/r³ pixel, 1/r² strip** | 663131 | 86.72% | 82.74% | 3.03% | 406 | +710 / −773 |
| off, Kalman refit of the seed | 659886 | 86.76% | 82.69% | 2.99% | 409 | +678 / −918 |
| on, transverse gap ≥ 60 mm | 663509 | 86.83% | 82.80% | 3.04% | 429 | +527 / −334 |
| **on, fit all SPs, 1/r³ pixel, 1/r² strip** | 664322 | 86.86% | 82.86% | 3.05% | 421 | +649 / −242 |

Down-weighting helps up to 1/r³ for pixels and 1/r² for strips. Strip seeds break from 1/r⁴ on (estimation failures double) and pixel seeds at 1/r⁶ (almost no tracks). HS differences are tens of particles out of 17908, so about 2σ at best.

Track-finding CPU against forcing on (serial, 3 cycles, scatter ≤ 0.6%): forcing off +2.4%, off + fit +4.9%, on + fit +2.0%."""
R["LOCAL"] = """Dumps of the estimate against the fitted track at the first space point, on 207885 truth-pure pixel seeds, 100 events, binned by the transverse gap between SP0 and SP2. Errors are core widths (scaled MAD).

| SP0–SP2 Δr [mm] | seeds | φ error, default [mrad] | φ error, first three | θ error, default | θ error, first three | q/p error, default | q/p error, first three |
|---|---|---|---|---|---|---|---|
| 0–10 | 56564 | 1.04 | 5.21 | 0.28 | 0.16 | 23% | 195% |
| 10–20 | 28663 | 1.12 | 3.65 | 0.39 | 0.21 | 20% | 84% |
| 20–30 | 12809 | 1.29 | 3.33 | 0.28 | 0.13 | 30% | 52% |
| 30–40 | 5577 | 1.35 | 3.56 | 0.45 | 0.12 | 19% | 32% |
| 40–60 | 25707 | 1.34 | 2.46 | 0.79 | 0.36 | 11% | 21% |
| 60–80 | 19236 | 1.28 | 2.29 | 1.19 | 0.70 | 9% | 18% |
| 80–120 | 4296 | 1.29 | 1.86 | 1.55 | 0.99 | 8% | 12% |
| > 120 | 55033 | 1.23 | 0.83 | 2.08 | 1.17 | 5% | 7% |

The local triplet does what was hoped for θ: it is about twice as good everywhere, because it avoids the scattering in the chord. φ and q/p come from the transverse plane, and there the distances are too short. At |η| ≥ 2 the φ error is 3.4–6 mrad and flat in pT, so it is resolution rather than scattering. In the barrel at pT < 1 GeV the local φ is better than the default (1.07 vs 1.82 mrad).

**Threshold.** The existing MinDeltaR mode cuts on the difference in distance from the origin. In the forward region that distance is long even when Δr is tiny, so it almost never triggers, and mode 3 came out the same as mode 0 (657345 vs 657350 tracks). A cut on the transverse gap does work. Most of the repair comes from taking q/p from first/middle/last (PU 82.20% → 82.58%); the transverse gap adds another 0.1% (82.68%), and at |η| ≥ 2.5 HS goes from 88.27% to 89.76%. It stays below the weighted fit, which uses every point instead of selecting three. The transverse options exist only in the diagnostic build, and I did not measure their CPU."""
R["CPU"] = """Timing: the fit costs +1.8% of track finding without forcing (12584 → 12806 ms per 20 events) and +2.1% with forcing. (I first quoted 2.5%; these are the measured differences.)

Profile (`perf`, 10 events, LRT off, forcing off, 1999 Hz, samples under `TrackFindingAlg::execute`):

| | first/middle/last | all-SP fit |
|---|---|---|
| total | 11773 | 11901 |
| CKF | 10718 | 10757 |
| seed parameter estimation | 623 | 706 |
| of which triplet estimate | 77 | 7 |
| of which helix fit | 0 | 71 |
| of which, inside the fit, eigensolver | 0 | 43 |
| of which `std::pow` for the weights | 0 | 21 |
| of which reading SP x/y/z (`xAOD::SpacePoint_v1::z`) | 47 | 84 |
| of which propagation to the surface | 344 | 303 |

The estimation step grows by 83 samples, 0.7% of track finding or about 1 µs per seed. The other 1% of the timing difference is not resolved: the CKF moves by +39 samples with a statistical error of about ±150, and start parameters that differ change what the CKF does.

There is some room. `Acts::detail::fitCircleTaubin` calls Eigen's iterative `GeneralizedSelfAdjointEigenSolver`, although the second matrix is diagonal; rescaling makes it an ordinary 3×3 problem with a closed-form or Newton solution. The weight exponents are integers, so `std::pow` can be multiplications. Together that is at most about 60 samples, 0.5% of track finding. This is an estimate from the profile; I did not implement it. The remaining cost is reading all the space points, which any all-point fit has to do."""
R["WRONG"] = """Truth per space point from the dump, 100 events, seeds with a candidate track. A space point is wrong if any of its clusters is not from the particle that owns most of the seed's space points. *No majority* means no particle owns more than half.

![pixel](2026-11-11_stay-on-seed-gbts/gbts-wrong-sp-pixel.png)

![strip](2026-11-11_stay-on-seed-gbts/gbts-wrong-sp-strip.png)

| seeds | pixel | selected only with / without forcing | strip | selected only with / without forcing |
|---|---|---|---|---|
| pure | 238542 (93.77%) | 888 / 27 | 17972 (62.57%) | 358 / 17 |
| wrong at the back | 7658 (3.01%) | 76 / 95 | 1918 (6.68%) | 101 / 42 |
| wrong at the front | 5772 (2.27%) | 166 / 6 | 3019 (10.51%) | 44 / 8 |
| wrong in the middle | 870 (0.34%) | 12 / 6 | 687 (2.39%) | 35 / 14 |
| several places | 240 (0.09%) | 18 / 3 | 12 (0.04%) | 0 / 1 |
| no majority | 1321 (0.52%) | 46 / 23 | 5117 (17.81%) | 28 / 25 |

- Runs are short. 97.3% of pixel seeds with a wrong space point have a single one (14142 of 14540); only 35 have a run of 3 or more at the front or back. Strip seeds: 99.8%.
- Pixel position depends on η. Up to |η| ≈ 2 the wrong point is mostly the first one. At |η| 2.5–3.5 it is mostly the last one.
- Of the wrong pixel space points, 46% have no truth particle at all (6969 of 15260) and 54% belong to another particle. I did not separate noise from untracked secondaries.
- Strip seeds are much less clean. Half of their wrong space points (2909 of 5658) combine clusters of two particles, which are ghost space points.
- Forcing is neutral on back-wrong pixel seeds, gains on front-wrong ones, and the bulk of its gain is on pure seeds, which confirms section 1."""
R["REVERSE"] = """Tested on the MR 92380 build, reversing every primary seed (`autoReverseSearch`, `useTopSpRZboundary=[0,0]`, `twoWaySmoothing=True`). With reverse off that build reproduces main exactly. The first pass then starts at the top space point and runs inward.

| variant | tracks | eff HS | eff PU | fakes | dupl. | PU \\|η\\|<1.5 | PU 1.5–2.5 | PU ≥2.5 |
|---|---|---|---|---|---|---|---|---|
| forward, forcing on (main) | 663332 | 86.83% | 82.75% | 3.04% | 436 | 81.08 | 80.56 | 86.62 |
| forward, forcing off | 661409 | 86.61% | 82.55% | 3.02% | 415 | 80.91 | 80.33 | 86.41 |
| reverse, on, no second-pass stopper | 563072 | 80.76% | 73.65% | 3.05% | 186 | 79.24 | 66.87 | 72.01 |
| reverse, on | 626949 | 85.66% | 80.20% | 3.24% | 1131 | 81.13 | 80.79 | 78.55 |
| reverse, off | 614499 | 84.47% | 78.64% | 3.19% | 1053 | 80.98 | 80.26 | 74.37 |
| reverse, on, fit weighted to the outer SPs (r³/r²) | 633651 | 85.96% | 80.93% | 3.26% | 1150 | 81.30 | 80.92 | 80.47 |
| reverse, off, same fit | 622709 | 84.97% | 79.55% | 3.22% | 1076 | 81.22 | 80.64 | 76.57 |
| *diagnostic:* reverse, on, field at the innermost SP | 667798 | 86.87% | 82.77% | 3.48% | 1332 | 81.13 | 80.85 | 86.38 |
| *diagnostic:* reverse, off, field at the innermost SP | 659677 | 86.34% | 81.90% | 3.44% | 1262 | 80.97 | 80.35 | 84.34 |

All rows except the two diagnostic ones use the field at the estimation point, which is what we want.

- **The second-pass stopper is required.** Without it the long outward leg runs past the end of the track, as in the LRT case. This is `doSecondPassBranchStopper`, on only for LRT today.
- **Up to |η| 2.5 reverse is as good as forward**, slightly better at 1.5–2.5, and the outer-weighted fit gives the best numbers of the whole study there (PU 81.30 and 80.92).
- **At |η| ≥ 2.5 it loses 8%.** The two diagnostic rows locate the cause in the estimate: moving only the field point recovers nearly all of it. First/middle/last fits one radius over the whole seed and converts it with the field at one end, and at the top of a forward seed that field is not representative of the arc. So with the field at the estimation point, the estimate must be local to that point, or q/p needs the field averaged along the arc. The outer-weighted fit recovers part of the loss, in line with this. I have not tested an arc-averaged field.
- **It does not remove the need for forcing.** The on/off gap grows: 1.56% PU in reverse against 0.20% forward, and still 0.87% with the diagnostic field. Mis-picks happen from the top as well.
- **Duplicates triple and fakes rise** (3.24% vs 3.04%, more at high η). I did not look into why.

@@REVCPU@@"""
for k, v in R.items(): s = s.replace(f"@@{k}@@", v)
open(N, "w").write(s)
