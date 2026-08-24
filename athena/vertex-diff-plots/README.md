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

Runs on any CERN box with cvmfs; lxplus is not required. The EOS side needs a
Kerberos ticket — **uppercase realm**, `kinit user@cern.ch` fails
pre-authentication because only `CERN.CH` is defined in
`/etc/krb5.conf.d/cern-realm-cernch.conf`.

```bash
kinit $USER@CERN.CH
mkdir -p ~/acts475-vtx && cd ~/acts475-vtx
~/cern/scripts/athena/vertex-diff-plots/run_all.sh
```

`run_all.sh` sets up its own environments, checks every input is readable before
doing any work, caches the `.npz` extractions (delete them to force a re-read),
and writes `plots/<sample>/` plus a combined `plots/ALL_summary.md`. Restrict the
set with `SAMPLES="q454 q449" ./run_all.sh`.

### Two stages, two environments

No single environment has both halves, so `setup_env.sh` provides each:

| stage | environment | why |
|---|---|---|
| `extract_pv.py` | `AnalysisBase,25.2.107` | ROOT + xAOD dictionaries. A full Athena release works too, but AnalysisBase is much smaller and enough — the script only reads the transient tree. |
| `compare_pv.py` | `LCG_109/x86_64-el9-gcc13-opt` | numpy + matplotlib, which AnalysisBase does not ship. |

Override with `ANALYSIS_BASE_VERSION` / `LCG_VIEW`.

**Trap:** never `set -e` or `set -u` around `atlasLocalSetup`, `asetup` or an LCG
`setup.sh`. All three return non-zero and dereference unset variables, and under
either flag they kill the calling shell silently — empty log, exit status 0,
nothing to indicate anything ran. Cost an hour the first time.

| file | what it does |
|---|---|
| `extract_pv.py` | one xAOD → one `.npz`: per-vertex position, covariance, χ², nDoF, track weights, plus tau track/jet variables. Reads via the xAOD transient tree, so it needs Athena or AnalysisBase. |
| `compare_pv.py` | two `.npz` → 11 figures, each as PNG **and** PDF, + `summary.md`. Pure numpy/matplotlib, no ROOT. |
| `affected_fraction.py` | reference `.npz` + the CI `diff-root` counts → the affected-vertex **fraction**. The CI log has the numerator but never the denominator; the reference dumps supply it. |
| `setup_env.sh` | environment bootstrap, `source setup_env.sh {extract\|compare}`. |
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

Every figure is written twice, `.png` and `.pdf` — PNG to paste into the MR
thread, PDF because the pulls sit around 1e-6 and only stay readable zoomed in.

## Reading `summary.md`

The rows that decide the thread:

- `dz/sz` median and max — the headline number. Measured: 6.8e-5 at worst.
- `vertices_changed_frac` — the affected-vertex fraction, which the CI logs give
  no denominator for. Measured: 84.2%, against the "~2–4%" the notes carry over
  from a standalone ACTS A/B.
- `events_nvtx_changed` — must be 0 (independently implied by the absence of
  dump-desync warnings in the CI logs). Measured: 0.
- `vertices_ntrk_changed` — **not covered by any existing check.** A track
  leaving a vertex matters more than a weight wiggling. Measured: 0.
- `hs_vertex_reassigned` — must be 0; the only failure mode with real physics
  consequences. Measured: 0.

See [Results](#results--measured-2026-08-24) for the full tables.

## Scope

This measures the size of the perturbation, not tracking/vertexing
**performance**. Efficiency, fake rate and HS-selection efficiency vs μ need
IDPVM + DCube on an O(1000)-event sample, i.e. a real reco campaign on both
sides — pointless at 25 events per CI sample, which is why the paired approach
is used here.

## Results — measured 2026-08-24

Full run over the five CI samples, 180 events, 2724 vertices. All EOS inputs
were still present.

### The answer to the thread

| sample | max \|Δz\| | median Δz/σz | **max Δz/σz** |
|---|---|---|---|
| q442 RecoRun2Data | 2.4e-3 µm | 1.5e-6 | 2.7e-5 |
| q452 RecoRun2MC | 0 | 0 | 0 |
| q449 RecoRun3Data_Checks | 7.6e-3 µm | 2.7e-6 | **6.8e-5** |
| q454 RecoRun3MC | 0 | 0 | 0 |
| q447 RecoRun4MC | 0 | 0 | 0 |

**The largest position shift anywhere is 7.6 pm, and the largest shift relative
to the vertex's own fitted resolution is 6.8e-5** — roughly 15 000× below the
resolution, and 150× below the ~1e-2 level at which the runbook said escalation
to IDPVM would be warranted. The two MC Run2/Run3 samples do not move a vertex
position at all; only the weights and χ² move there.

### The three checks that had to come out zero, and did

| check | result |
|---|---|
| `events_nvtx_changed` | **0** in all five samples |
| `vertices_ntrk_changed` | **0** in all five samples |
| `hs_vertex_reassigned` | **0** in all five samples |

`vertices_ntrk_changed` was the one not covered by any existing check — the CI
dump-desync argument proves `nVtx` is unchanged but says nothing about the number
of tracks attached to a vertex. It is unchanged too: every vertex has a
bit-identical track multiplicity, and the total track-weight count matches
per sample (8276, 1332, 43554, 1577, 227).

### Affected-vertex fraction

| sample | vertices | weight vector changed | covariance changed | CI `trackWeights` |
|---|---|---|---|---|
| q442 | 477 | 403 (84.5%) | 341 | 403 ✓ |
| q452 | 52 | 27 (51.9%) | 26 | 27 ✓ |
| q449 | 2126 | 1829 (86.0%) | 1466 | 1111 (CI saw 60/100 events) |
| q454 | 53 | 26 (49.1%) | 26 | 26 ✓ |
| q447 | 16 | 8 (50.0%) | 9 | 8 ✓ |
| **total** | **2724** | **2293 (84.2%)** | **1868** | |

**84.2%, not the ~2–4% carried over from the standalone ACTS A/B.** That figure
came from 155/159 vertices bitwise identical in a Pythia8 1+50 PU sample and does
not transfer: at float32 in Athena, with the real field map and material, most
vertices land on the other side of the threshold. It does not weaken the
"insignificant" case, which rests on the magnitude above, but the MR thread
should not quote 2–4%.

Where `diff-root` saw every event, the measured per-vertex counts reproduce its
leaf counts **exactly** — 403/403, 27/27, 26/26, 8/8 and 341/341, 26/26, 26/26,
9/9. That is a strong check that `extract_pv.py` sees what the frozen-Tier0
comparison saw. q449 is the only mismatch and only because `diff-root` stopped at
event 60; 1829 × 0.6 ≈ 1100 against its 1111.

### Event ordering — correction to the runbook

The runbook states the two files hold the same events *in the same order*. True
for four samples, **false for q449**: same 100 events, 84 of them in a different
position. Everything here matches on `(run, event, vertex index)` rather than row
position, so it is unaffected — but any entry-by-entry comparison of that sample
would compare unrelated events. `diff-root` evidently orders the trees; a naive
`TTree::Scan` diff would not.

## Validation

- `extract_pv.py` — run against all ten AODs (both sides of five samples, 2724
  vertices per side). Works. Only `TauJetsAuxDyn.absipSigLeadTrk` comes back
  all-NaN; it is not on those AODs, and the `isAvailable` guard handles it.
- `compare_pv.py` — run on synthetic `.npz` (identical base truth, ~1e-7
  perturbation on 30% of vertices) and on a real null pair (`q447_ref` against
  itself). All 11 figures and the summary render; the null pair reports zero
  across every row, as it must.
- `run_all.sh` — run end to end over all five samples on 2026-08-24; input gate
  also exercised against a missing EOS side.
- Strongest external check: the measured per-vertex counts reproduce the CI
  `diff-root` leaf counts exactly on the four samples where `diff-root` saw every
  event (see above).
