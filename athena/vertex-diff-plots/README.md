# Paired vertex-diff plots — ACTS 47.5.0 bump

Quantifies the `PrimaryVertices` output change in
[athena!90327](https://gitlab.cern.ch/atlas/athena/-/merge_requests/90327)
(ACTS 47.5.0), to answer "are these vertex differences insignificant?".

Full context, input paths, and how to read the results:
`~/cern/notes/atlas/tsi/notebook/2026-08-24_acts-47.5.0-vertex-diff-plot-runbook.md`

## Why paired, not overlay+ratio

The reference and new AOD hold the **same events, same order, bit-identical
tracks** (all AOD digests pass). Overlaying the two `z` distributions gives two
identical curves and a ratio of 1.0 with huge error bars from 25 events — it
shows nothing, and reads as "no difference" when ~82% of events changed
somewhere. So everything here is a **per-matched-vertex difference**: vertices
are matched on `(run, event, vertex index)`, track weights on
`(run, event, vertex, track)`. That discards the sample variance we do not care
about and measures the shift itself.

**Headline output: `fig02_delta_position_pull.png` — Δz/σ_z.** "Insignificant"
means the shift sits far below the vertex's own fitted resolution.

## Usage

On lxplus (needs EOS + the cvmfs WorkflowReferences tree):

```bash
setupATLAS && asetup Athena,main,latest
kinit $USER@CERN.CH
mkdir -p ~/acts475-vtx && cd ~/acts475-vtx
~/cern/scripts/athena/vertex-diff-plots/run_all.sh
```

`run_all.sh` checks every input is readable before doing any work, caches the
`.npz` extractions (delete them to force a re-read), and writes
`plots/<sample>/` plus a combined `plots/ALL_summary.md`. Restrict the set with
`SAMPLES="q454 q449" ./run_all.sh`.

| file | what it does |
|---|---|
| `extract_pv.py` | one xAOD → one `.npz`: per-vertex position, covariance, χ², nDoF, track weights, plus tau track/jet variables. Reads via the xAOD transient tree, so it needs Athena or AnalysisBase. |
| `compare_pv.py` | two `.npz` → 11 figures + `summary.md`. Pure numpy/matplotlib, no ROOT. |
| `run_all.sh` | driver over the five CI samples (q442 q452 q449 q454 q447). |

## Figures

| file | content |
|---|---|
| `fig01_delta_position` | Δx, Δy, Δz [µm] |
| **`fig02_delta_position_pull`** | **Δx/σx, Δy/σy, Δz/σz — the headline** |
| `fig03_delta_fitquality` | Δχ², Δ(χ²/nDoF), ΔnDoF |
| `fig04_delta_weights` | Δ(track weight), Δ(Σw), Δ(n tracks/vertex) — the root cause, acts#5672 |
| `fig05_delta_sigma` | σ_new/σ_old − 1 |
| `fig06_trends` | \|Δz\| vs z, vs n tracks, vs σz — bias / trend check |
| `fig07_nvtx` | vertex multiplicity, ref vs new |
| `fig08_hs_vertex` | hard-scatter vertex PV[0]; flags any reassignment (>1 mm) |
| `fig09_tau_tracks`, `fig10_tau_jets` | downstream tau TJVA and RNN scores, old vs new |
| `fig11_overlays` | unpaired overlays + difference panel, for completeness only |

Each Δ panel pair is: |Δ| on log-x (median and max marked) and the signed
distribution restricted to entries that actually changed, clipped at p99.

## Reading `summary.md`

The rows that decide the thread:

- `vertices_changed_frac` — the affected-vertex fraction, **not currently known
  from the CI logs**; the note's "~2–4%" comes from a standalone ACTS A/B, not
  from Athena.
- `dz/sz` median — the headline number.
- `events_nvtx_changed` — must be 0 (independently implied by the absence of
  dump-desync warnings in the CI logs).
- `vertices_ntrk_changed` — **not covered by any existing check.** A track
  leaving a vertex matters more than a weight wiggling.
- `hs_vertex_reassigned` — must be 0; the only failure mode with real physics
  consequences.

## Scope

This measures the size of the perturbation, not tracking/vertexing
**performance**. Efficiency, fake rate and HS-selection efficiency vs μ need
IDPVM + DCube on an O(1000)-event sample, i.e. a real reco campaign on both
sides — pointless at 25 events per CI sample, which is why the paired approach
is used here.

## Validation

`compare_pv.py` was exercised end to end on synthetic `.npz` input (identical
base truth, ~1e-7 perturbation on 30% of vertices) — all 11 figures and the
summary render correctly. `extract_pv.py` is syntax-checked only; it has not
been run against a real xAOD, since that needs Athena.
