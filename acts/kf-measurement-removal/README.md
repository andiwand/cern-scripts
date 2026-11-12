# Removing a measurement from a smoothed Kalman track

Check of the removal of a measurement, or of the start prior, from a smoothed
Kalman track without a refit, against a refit and a dense least-squares fit in
the linear-Gaussian model. The note is
`cern-notes/acts/notebook/2026-11-12_gbts-seed-range-fit-not-search.md`.

## Scripts

- `removal_check.py`: 200 random systems, RNG seed 1112, 9 states with 5
  parameters, 2-dimensional measurements, process noise on 3 of the 5
  components. It checks the update with `-V` at the state, the conditioning
  walks to the other states with the stored gains, the chi2 change, the first
  and the last measurement, two removals in a row with refreshed gains, and
  the removal of the prior for prior widths 0.01, 1, 100 and 1e4 against a
  dense fit without a prior. It asserts agreement to `1e-6`; the prior widths
  0.01 and 1e4 are reported only. Needs NumPy.

Run with `uv run --no-project --with numpy python -I removal_check.py`.
