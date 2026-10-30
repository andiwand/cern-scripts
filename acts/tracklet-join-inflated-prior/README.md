# Tracklet join with an inflated pass-2 prior

Check of the two-way CKF join when pass 2 starts from the pass-1 smoothed
parameters with the covariance inflated by a factor `c`, against a dense joint
linear-Gaussian fit. The note is
`cern-notes/acts/notebook/2026-10-30_two-way-ckf-inflated-prior-join.md`.

## Scripts

- `inflated_prior_check.py`: 100 random six-dimensional two-arm systems, RNG
  seed 812, inflation factors 1, 4, 10, 100, 1000 and 1e6, in a full-rank and
  a rank-deficient configuration. It checks the prior-node step, the
  combination at the shared node in the covariance form and in the MBF form
  (re-anchored adjoint), the conditioning walks over both arms in the RTS and
  the MBF form, the prior independence of the regression coefficients, a
  wrong prior mean, and the error without the prior subtraction. It asserts
  agreement to `1e-8` for `c <= 1000`. `c = 1e6` and the filter diagnostic
  row (absolute error on quantities of size `c`) are reported only. Needs
  NumPy.

Run with `uv run --no-project --with numpy python -I inflated_prior_check.py`.
