#!/usr/bin/env python3
"""Write the concise reviewed note/MR after the complete campaign is archived."""
import json
from pathlib import Path
n=Path('/home/astefl/notes/atlas/tsi/notebook')
a=n/'2026-11-24_native-pixel-nn-final-candidate/mr-review/generic'
r=Path('/home/astefl/source/acts/acts-athena-ci/run/native-pixel-nn')
s=json.loads((a/'full/integration.json').read_text())
f=json.loads((a/'full/record-comparison.json').read_text())
t=json.loads((a/'full/timing.json').read_text())['summary']
loc=json.loads((a/'loc.json').read_text())['totals']
assert s['comparison']['gained']==s['comparison']['lost']==0
assert s['comparison']['tracking_counters_equal']
assert f['truth_and_event_records_equal'] and f['non_kinematic_track_records_equal']
p=s['physics']['Native'];q=s['physics']['OnnxRuntime']
assert all(p[k]==q[k] for k in ('truth','matched','fakes','reco','duplicate_truth'))
ckf=s['normalized']['ckf_ms'];event=s['normalized']['event_ms']
revision=(a/'full/source-commit.txt').read_text().strip()[:11]
breakdown=[loc[k]['net'] for k in ('conversion','inference','glue','tests')]
total=sum(breakdown)
text=f'''# Native pixel NN: final candidate

2026-11-24; reviewed 2026-11-25. Branch `acts-native-pixel-nn`, commit `{revision}`, based on Athena main `41da040949e`. [Draft MR !92770](https://gitlab.cern.ch/atlas/athena/-/merge_requests/92770).

Keep runtime-sized native inference: changed depths/widths need no recompilation, at little cost on current models. Native is the default preference; failed construction logs the reason and falls back to ONNX per model. `PixelNNInferenceBackend.OnnxRuntime` selects ONNX directly.

## Implementation

- `IPixelClusterNN` hides the backend. A factory and `PixelClusterNNCondAlg` populate `PixelClusterNNCollection`; legacy ONNX conditions match main. ACTS uses the common interface, with its obsolete ONNX wrapper removed.
- Native reads dense/SiLU layer counts and dimensions from ONNX. Shared enums/vector aliases retain the 67-feature input and number/position output contract. The factory accommodates future implementations.
- CxxUtils GEMV/vector arithmetic, Eigen SIMD exp, 64-byte-aligned weights/biases. Runtime loops use fixed register blocks; per-call scratch uses stack storage up to width 128, then heap.
- Separate conversion/consistency helpers check tensor names/types/shapes/finiteness and compare 64 inputs against ONNX. No SHA/OpenSSL dependency. Probes do not prove graph equivalence. Native models retain no ONNX session after loading.

Dispatch checks AVX2/FMA once per model; `SICLUSTERIZATION_NATIVE_NN_AVX2=OFF` omits that kernel. Shared-source kernels use hidden symbols and inline Eigen helpers to isolate ISA implementations. Calibration strategy, charge/size gates and tracking cuts remain separate.

## Compute

Number plus selected position, actual Athena GCC library: **{t['auto']['mean_us']:.2f} ± {t['auto']['sd_us']:.2f} μs AVX2**, **{t['sse']['mean_us']:.2f} ± {t['sse']['sd_us']:.2f} μs SSE**, ONNX **{t['onnx']['mean_us']:.2f} ± {t['onnx']['sd_us']:.2f} μs**. Three alternating cycles × 50k captured inputs × three repeats; excludes loading/cluster preparation. Threadripper 3970X/core 16, GCC 15.2, `-O2`, no fast-math.

Separate paired standalone comparison against the frozen fixed-size candidate, same sample/repeats; Clang 20.1.8:

| Compiler / kernel | Fixed-size [μs] | Runtime-sized [μs] | Change |
| --- | ---: | ---: | ---: |
| GCC / AVX2 | 1.824 | 1.821 ± 0.017 | −0.1% |
| GCC / SSE | 3.226 | 3.258 ± 0.010 | +1.0% |
| Clang / AVX2 | 2.173 | 2.285 ± 0.059 | +5.1% |
| Clang / SSE | 3.234 | 3.268 ± 0.020 | +1.1% |

Fresh integration, three alternating serial 20-event pairs, normalized to pixel clusterization: **CKF CPU {ckf['change_pct']:.1f} ± {ckf['sd_pct']:.1f}%**, **event CPU {event['change_pct']:.1f} ± {event['sd_pct']:.1f}%** versus ONNX. Uncertainties are cycle SDs.

## Physics and validation

Fresh 100-event ttbar μ=200 runs per backend, NN post-calibration at all charges/sizes:

| Quantity | ONNX and Native |
| --- | ---: |
| Efficiency | {p['matched']:,} / {p['truth']:,} = {p['efficiency_pct']:.5f}% |
| Fakes / tracks | {p['fakes']:,} / {p['reco']:,} = {p['fake_pct']:.5f}% |
| Duplicate truth particles | {p['duplicate_truth']} |

No gained/lost truth; truth associations, hit summaries and all {s['comparison']['tracking_counter_rows']} tracking-counter rows agree. Fitted floats differ: pT p99 absolute difference {f['differences']['pt_MeV']['p99_abs']:.4f} MeV, maximum relative difference {100*f['differences']['pt_MeV']['max_relative']:.3f}%.

- 4/4 unit/configuration tests pass with AVX2 ON and OFF; restored ON code/data match the measured libraries. Tests include shallow/deep/wide/decoder-only models, concurrency, invalid shapes, metadata and fallback.
- Actual Athena library: all four heads on 100k captured inputs, auto/forced-SSE versus ONNX, within `1e-5 + 1e-4 × |reference|`; no multiplicity-choice changes. GCC/Clang checks cover another 10k-input comparison. GCC/AVX2 is not bit-identical to the fixed candidate.
- Pre-calibration and default-threshold smoke counters agree. An incompatible-activation model logs native rejection and reconstructs through ONNX. Ordinary native jobs have no fallback warnings.
- GCC/Clang release/debug/instrumented-object ISA audits pass; instrumented objects were inspected, not executed. No non-AVX hardware was available. ACTS restoration excludes a debug-metadata/build-ID change from whitespace cleanup.

<details markdown="1">
<summary>Selection and limits</summary>

Nov 23 gcc15 nightly / ACTS 48.5.0; four physics threads, serial timing with 19 timed events/job, main’s seed policy. Truth: stable charged generator particles, pT > 1 GeV, |η| < 4, production radius < 300 mm when available; match probability > 0.5. Fakes: reconstructed |η| < 4 tracks with probability < 0.5 or missing/nonfinite probability. The {p['half']} tracks exactly at 0.5 are separate. Finite-sample agreement is not universal decision equivalence.

</details>

## Code size

| Net LOC | Conversion/validation | Inference/types/dispatch | Glue | Tests | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current MR | {breakdown[0]} | {breakdown[1]} | {breakdown[2]} | {breakdown[3]} | {total} |

Net nonblank/noncomment additions versus main, including headers/build/configuration; glue includes the factory/ONNX adapter. Tests include the fixture generator; ~95 KiB binary fixtures are excluded. No generated inference code. Fixed-size checkpoint: 648 lines.

<details markdown="1">
<summary>Earlier choices and exponential width</summary>

Intrinsics → Eigen → CxxUtils: explicit GEMV blocking and vector SiLU blend/division provide performance and runtime dispatch. Keep Eigen’s measured exp; no custom exponential. `Eigen::Map` already reads scratch packets without copying.

Exp width could be independent of GEMV width. The earlier shared-SSE SiLU experiment cost 0.35–0.46 μs including its call boundary; it does not isolate exp width. Shared exp-only and `libmvec` remain unmeasured. The 64-byte alignment trial suggests a 2–3% SSE benefit, no convincing AVX2 gain.

[Backend survey](2026-11-24_nn-inference-latency.md): ONNX, SOFIE, LWTNN. [Eigen study](2026-11-24_native-pixel-nn.md): integration, compile-time AVX2, roofline. [First CxxUtils report](2026-11-24_native-pixel-nn-cxxutils.md): shared SSE activation.

Athena dispatch precedents: [GSF](https://gitlab.cern.ch/atlas/athena/-/blob/41da040949efeca5de0e5adbd84054868a5165c6/Tracking/TrkFitter/TrkGaussianSumFilterUtils/src/KLGaussianMixtureReduction.cxx#L27), [field interpolation](https://gitlab.cern.ch/atlas/athena/-/blob/41da040949efeca5de0e5adbd84054868a5165c6/MagneticField/MagFieldElements/src/BFieldCache.cxx#L10), [calorimeter corrections](https://gitlab.cern.ch/atlas/athena/-/blob/41da040949efeca5de0e5adbd84054868a5165c6/Calorimeter/CaloLumiConditions/src/CaloBCIDCoeffs.cxx#L50).

</details>

[Review/evidence](2026-11-24_native-pixel-nn-final-candidate/mr-review/generic/review.json), [integration](2026-11-24_native-pixel-nn-final-candidate/mr-review/generic/full/integration.json), [isolated timing](2026-11-24_native-pixel-nn-final-candidate/mr-review/generic/full/timing.json), [LOC](2026-11-24_native-pixel-nn-final-candidate/mr-review/generic/loc.json), [standalone HTML](2026-11-24_native-pixel-nn-final-candidate.html). Scripts: `athena/acts-athena-ci/native-pixel-nn` in `~/scripts`.
'''
assert len(text.split())<=880,len(text.split())
(n/'2026-11-24_native-pixel-nn-final-candidate.md').write_text(text)
body=f'''🤖 Prefer native ACTS pixel NN inference using existing ONNX weights and runtime-sized depths/widths. A common interface provides logged ONNX fallback when native construction fails. Explicit ONNX remains available; legacy ONNX conditions stay unchanged.

We tried intrinsics and Eigen, then chose CxxUtils for performance and SSE/AVX2 runtime dispatch; Eigen supplies exp.

Number + selected position, μs/cluster (GCC 15, Threadripper 3970X):

| Backend | Inference [μs] | LOC total / conversion / inference / glue / generated / tests |
| --- | ---: | --- |
| ONNX Runtime | {t['onnx']['mean_us']:.1f} | 45 / 0 / 45 / — / 0 / — |
| Native | {t['auto']['mean_us']:.1f} AVX2<br>{t['sse']['mean_us']:.1f} SSE | {total} / {breakdown[0]} / {breakdown[1]} / {breakdown[2]} / 0 / {breakdown[3]} |
| LWTNN float | 6.8 | 46 / 21 / 25 / — / 0 / — |
| SOFIE/GEMV (patched) | 6.0 | 1,088 / 82 / 26 / — / 980 / — |

Net LOC excludes blanks/comments/library code. Native includes shared glue/tests and the ONNX adapter; — marks uncounted support. LWTNN/SOFIE are earlier prototypes.

100 ttbar μ=200 events, all-cluster NN post-calibration: both {p['efficiency_pct']:.5f}% efficiency and {p['fakes']}/{p['reco']:,} fakes; no gained/lost truth. Three serial timing pairs: CKF {ckf['change_pct']:.1f}%, event {event['change_pct']:.1f}% versus ONNX.

4/4 tests pass with AVX2 ON/OFF; 100k-input comparisons, GCC/Clang ISA audits, pre/default-threshold and fallback smoke checks pass.
'''
assert len(body.split())<=224,len(body.split())
(r/'mr-description.md').write_text(body)
(r/'mr-update.json').write_text(json.dumps({'description':body}))
print('words: note',len(text.split()),'MR',len(body.split()))
