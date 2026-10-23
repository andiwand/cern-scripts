# Fatras runtime hadronics without a custom event library

WP1 now has an optional **on-demand Geant4 backend**, implemented on ACTS branch
`feat/fatras-compact-hadronic`: `2d40fdbd4a` adds the native model interface,
`1c40488e7d` adds the backend, example factory and bindings. No fitted native
final-state generator is implemented. This is an alternative supported by an
existing Geant4 installation, including its standard datasets.

The native transport, EM physics, decays, charged thresholds and navigation stay
in Fatras. FTFP_BERT supplies inelastic rates and final states only. A silicon
reference target with local material L0 retains the previous material
approximation. Initialization and simulation must use the same thread; the
example factory uses the single Geant4Manager lifecycle. It cannot coexist with
a separate Geant4 setup in the same process. The replay backend remains an
explicit optional validation reference, not an input to the on-demand backend.

## Result — 15 October 2026

`results/2026-10-15/` contains:

- `inclusive_file_free.pdf`: uncut inclusive ID/pixel hits, momentum and process
  distributions, CPU and memory; ACTS main, replay Fatras, on-demand Fatras, G4.
- `spectra/final_states.pdf`: multiplicity, leading energy, rates and daughter
  momenta/angles, before transport cuts.
- `comparison.json`: underlying inclusive event counts and paired differences.
- `table-unavailable.json`: the successful five-event on-demand run executes
  inside a macOS sandbox denying reads of the existing custom table. An explicit
  attempted read fails with `PermissionError` before simulation starts.
- `input-reproduction.json`: input SHA256 matches against the archived reference.
- `footprint.json`, test/build logs, build commands/source hashes and run metadata.
- `changed/`, `live/`, `inputs/`: reproducibility data; generated CSVs are compressed
  where useful. Readers accept `.csv.gz` without changing their contents.

Five ttbar + fixed PU200 events, seed 42, 2 T, no input or analysis momentum cuts.
Only generator births inside the ID are retained. ACTS-main `300b664a3d` and
strictly ID-bounded default FTFP_BERT are archived 14 October references on these
**byte-identical** inputs. The new replay reproduces the archived hit counts,
pT histograms and process counts exactly. New replay/live timings are sequential
15 October measurements, one worker, with the same CSV writers; do not interpret
the archived main/G4 timings as new concurrent measurements.

| Model | ID secondary hits/event | Pixel secondary hits/event | CPU s/event | Setup CPU s/job | Peak RSS MiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| ACTS main (archived) | 12742.0 | 5538.8 | 0.790 | 1.12 | 570 |
| Replay Fatras | 44031.4 | 15465.8 | 1.067 | 10.38 | 1339 |
| On-demand Fatras | 43708.2 | 15220.0 | 1.359 | 1.38 | 639 |
| Geant4 ID (archived) | 120826.4 | 41260.2 | 40.059 | 1.56 | 4096 |

On-demand minus replay: ID −323 ± 721 hits/event; pixel −246 ± 357 (paired event
SEM, not systematic uncertainty). The custom-file blocker is removed for this
optional backend; the inclusive hit deficit and low-momentum transport problem
remain. Five events do not establish reconstruction fidelity or MT throughput.

## Normal ACTS use

Build this branch with `ACTS_BUILD_FATRAS_GEANT4=ON` and Python examples enabled.
Initialize `acts.examples.geant4.makeFatrasNuclearInteraction()` once and pass
its result as `nuclearInteractionModel` to `addFatras`. Leave
`nuclearInteractionTable` empty and use a one-thread sequencer. The Geant4-free
build remains available, but this on-demand backend requires Geant4.

`run.py --mode live` uses this normal public API. It requires `--source`,
`--build`, `--revision`, `--input`, `--output`, `--material-map`, and optionally
`--events`. Use `--mode changed --table FILE` for replay. `--mode geant4` retains
the existing strict ID-world helper (`id_world.so` in the charged-meson package)
and defaults, without added momentum/time kills. Main mode requires a genuine
main build. Activate the selected ACTS/Geant4 environment before running.

The recorded validation used a **macOS bridge into the existing d25514208b
build**, avoiding a rebuild of unrelated components in the user's main checkout.
`build-bridge.py --source SOURCE --build BUILD --output MODULE_DIR
--geant4-lib LIB_DIR` compiles the new Fatras simulation and production factory,
reusing that pinned build's core/framework/geometry. It is specific to that base
ABI. Pass `--module-dir MODULE_DIR` to `run.py` when using the bridge. Full normal
Python binding translation units also pass compilation; a clean full-project
CMake rebuild was not performed. See the archived build provenance.

## Isolated final-state validation

`build-benchmark.py --source benchmark.cpp --acts-source SOURCE --acts-build BUILD
--geant4-lib LIB_DIR --output EXECUTABLE` uses the existing build's compile flags
(macOS dylib environment). With standard G4 dataset environment active, run:

```sh
mkdir -p spectra
/path/to/benchmark spectra 512 /path/to/reference.table
python plot-spectra.py spectra
```

Omit the last argument for a genuinely file-free scan. The replay comparison
uses up to 512 distinct stored interactions per node, not repeated entries for
error bars. The scan checks four-momentum/charge accounting including the
residual, seeded repeatability, and caller-RNG restoration. A physical residual
check is also in the ACTS Geant4 unit test. General Geant4 closure discrepancies
are not used to reject and bias production samples.

`analyse.py --results RESULTS --reference ARCHIVED/inclusive-summary.json`
checks input hashes and inclusive accounting before plotting. It reads
`changed/` and `live/` and deliberately reuses the two archived reference series.
`reproduce-inputs.py` restores the reference CSV schema by removing only all-zero
optional ancestry columns, applies the ID birth boundary, and requires an exact
archived SHA256 match. `require-denied-table.py TABLE PROOF_JSON RUNNER ...` is
used *inside* an OS read-denial sandbox; it fails if the custom file is readable.

## Original byte audit

`audit-library.py TABLE --output OUTPUT_JSON` streams the V1 library, hashes each
byte and separates rate/header, event/remnant and daughter records. It is not a
physics validator. The 561 MiB file contains 771 nodes, 386304 interactions and
6364029 daughters; only about 32 KiB is rates/indexing. The final-state catalogue
accounts for 99.994% of its bytes. It remains outside ACTS for validation.

## Direct-model threading feasibility — 15 October 2026

The [standalone direct-model probe](direct-model/README.md) demonstrates concurrent
interaction generation without Geant4 run/event scheduling: identical outputs
across worker counts, 6.18× speedup at eight workers. MT-enabled Geant4 libraries,
standard datasets and per-worker particle state remain necessary. The production
ACTS adapter above is unchanged; full-event integration and throughput remain
unvalidated. [PDF](results/2026-10-15/direct-model/report/direct_model_validation.pdf).
