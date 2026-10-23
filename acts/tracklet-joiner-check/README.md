# Tracklet joiner check

Comparison of the two-way CKF output with and without the `TrackletJoiner`
(ACTS branch `feat-tracklet-joiner`). The note is
`cern-notes/acts/notebook/2026-10-23_tracklet-join-api-design.md`.

Both runs are `Examples/Scripts/Python/ckf_tracks.py` on the generic detector
with the default two-way finding, 100 events, seed 42.

## Scripts

- `compare_states.py <baseline trackstates_ckf.root> <joiner trackstates_ckf.root>`:
  robust widths (1.4826 MAD) of the smoothed pulls and residuals of all
  states, and their ratio.
- `compare_summary.py <baseline tracksummary_ckf.root> <joiner tracksummary_ckf.root>`:
  per-event sorted comparison of the perigee parameters, hit counts and chi2;
  they must be identical, because the joiner changes only the states.

Run with `uv run --no-project --with uproot --with awkward --with numpy python -I <script> ...`
in a shell without the ACTS environment.

## Single-thread timing

- `ckf_perf.py`: `ckf_tracks.py` with 100 muons per event, 200 events, one
  thread, and the `twoWaySmoothing` switch of the Examples track finding read
  from the environment variable `TWOWAY_SMOOTHING` (`1` or `0`). The source
  path of the configs is hard-wired to the `dev3` worktree. For main, drop the
  `twoWaySmoothing` keyword. The timing is the `Algorithm:TrackFindingAlgorithm`
  row of the sequencer table.
- Pitfall met on the way: `git stash` does not remove committed branch
  changes. A main baseline needs `git switch --detach <main commit>` and a
  check that the built library has no joiner symbols
  (`nm libActsExamplesTrackFinding.dylib | grep -c TrackletJoiner`).
