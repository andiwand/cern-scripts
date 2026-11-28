# Paired vertex-diff plots

Quantifies how much an MR (e.g. an ACTS bump) changes `PrimaryVertices` in the
frozen-Tier0 CI outputs, to answer "are these vertex differences
insignificant?". Built for athena!90327 (ACTS 47.5.0, runbook and results:
`atlas/tsi/notebook/2026-08-24_acts-47.5.0-vertex-diff-plot-runbook.md`), reused
for later bumps.

The reference and new AOD hold the same events with bit-identical tracks, so
overlaying distributions shows nothing. Everything here is a **per-matched-vertex
difference**: vertices matched on `(run, event, vertex index)` (not file
position: the order can differ), track weights on `(run, event, vertex, track)`.
Headline: `fig02_delta_position_pull` — Δz/σ_z, the shift relative to the
vertex's own fitted resolution. This measures the size of the perturbation, not
tracking/vertexing performance.

## Usage

Any CERN box with cvmfs. The EOS side needs a Kerberos ticket with the
**uppercase realm** (`kinit user@cern.ch` fails pre-authentication).

```bash
kinit $USER@CERN.CH
mkdir -p ~/cern/data/vertex-diff-plots/<mr> && cd ~/cern/data/vertex-diff-plots/<mr>
EOS_DIR=/eos/atlas/atlascerngroupdisk/proj-ascig/gitlabci/MR<nnnnn>_<sha> \
REF_VERSIONS="q442=v131 q452=v98 q449=v191 q454=v118 q447=v48" \
  ~/cern/scripts/athena/vertex-diff-plots/run_all.sh
```

`REF_VERSIONS` come from `Tools/WorkflowTestRunner/python/References.py` of the
MR; `EOS_DIR` may also be a local copy `<dir>/<test>/myAOD.pool.root`. Restrict
samples with `SAMPLES="q454 q449"`. `run_all.sh` checks every input first,
caches the `.npz` extractions (delete to re-read) and writes `plots/<sample>/`
plus `plots/ALL_summary.md`.

Two environments, set up by `setup_env.sh {extract|compare}` (override with
`ANALYSIS_BASE_VERSION` / `LCG_VIEW`): AnalysisBase for `extract_pv.py` (xAOD),
an LCG view for the numpy/matplotlib stages. Never `set -e`/`set -u` around
`atlasLocalSetup`, `asetup` or an LCG `setup.sh`: they kill the shell silently.

| file | what it does |
|---|---|
| `extract_pv.py` | one xAOD → one `.npz`: per-vertex position, covariance, χ², nDoF, track weights, tau track/jet variables |
| `compare_pv.py` | two `.npz` → 11 figures (PNG and PDF) + `summary.md` |
| `affected_fraction.py` | affected-vertex fraction, cross-checked against the CI `diff-root` counts (hard-coded for 90327; ignore the CI columns for other MRs) |
| `swapcheck.py` | vertex pairs that swap places in the sorted list (fake cm shifts), and the shift table without them |
| `run_all.sh`, `setup_env.sh` | driver over the five CI samples (q442 q452 q449 q454 q447), environments |

## Figures and summary

| file | content |
|---|---|
| `fig01_delta_position` | Δx, Δy, Δz [µm] |
| `fig02_delta_position_pull` | Δx/σx, Δy/σy, Δz/σz — the headline |
| `fig03_delta_fitquality` | Δχ², Δ(χ²/nDoF), ΔnDoF |
| `fig04_delta_weights` | Δ(track weight), Δ(Σw), Δ(n tracks/vertex) |
| `fig05_delta_sigma` | σ_new/σ_old − 1 |
| `fig06_trends` | \|Δz\| vs z, vs n tracks, vs σz |
| `fig07_nvtx` | vertex multiplicity, ref vs new |
| `fig08_hs_vertex` | hard-scatter vertex PV[0]; flags any reassignment (>1 mm) |
| `fig09_tau_tracks`, `fig10_tau_jets` | downstream tau TJVA and RNN scores |
| `fig11_overlays` | unpaired overlays, for completeness only |

In `summary.md`: `dz/sz` median and max (the headline), `vertices_changed_frac`,
and the three that must be 0 — `events_nvtx_changed`, `vertices_ntrk_changed`
(a track leaving a vertex; no CI check covers it), `hs_vertex_reassigned`.
