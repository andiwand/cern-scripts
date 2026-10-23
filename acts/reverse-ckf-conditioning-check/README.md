# Reverse CKF conditioning check

Check of the shared-state correction and the fixed-point endpoint update for the two-way CKF against a dense joint linear-Gaussian fit.
The note is `cern-notes/acts/notebook/2026-10-10_reverse-ckf-additional-options.md`.

## Scripts

- `conditioning_check.py`: 100 random six-dimensional systems, RNG seed 812. It asserts agreement to `1e-10`. Needs NumPy.
