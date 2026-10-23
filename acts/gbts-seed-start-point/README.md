# GBTS seed start point

Toy calculations for the choice of where the CKF starts on a GBTS seed.
The note is `cern-notes/acts/notebook/2026-10-23_gbts-seed-start-point.md`.

ITk-like barrel radii, eta 0, uniform 2 T, rough material. Nothing here runs ACTS.

## Scripts

- `gbts_bias.py`: noise-free circles through the GBTS tracking filter (transverse block) and the acts#6254 conversion. It prints the curvature ratio and the phi bias at the innermost node.
- `inner_hit_info.py`: sigma(curvature) with and without the innermost hit, no scattering.
- `layer0_prediction.py`: sigma of the predicted r-phi position at L0 from the outer hits, with correlated multiple scattering.

Run with any Python that has NumPy, for example `~/cern/venv/bin/python -I gbts_bias.py`.
