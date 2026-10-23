# Direct Geant4 models on independent workers

Feasibility result, 15 October 2026: **the hadronic generator can run concurrently
without Geant4's run manager or event scheduler**. This is a standalone probe,
not a replacement for the current ACTS adapter. Production ACTS code is unchanged.

Geant4 11.3.2 **MT libraries** and standard datasets remain dependencies. Each
ordinary C++ worker receives a Geant4 thread ID, particle workspace, empty
GenericIon process manager, independently owned Bertini/FTFP model graph,
cross-section stores and isolated RNG. The particle workspace permits nuclear
fragment creation. This uses Geant4's internal thread-local storage, but no
Geant4-created threads, run manager, transport event or worker run manager.

Initialization is serialized and shared tables are initialized first. Sampling
has no application mutex; Geant4 may synchronize internal ion/data registries.
The direct executable and its Geant4 dependency graph exclude `G4run`, `G4event`,
`G4tracking` and `G4physicslists`. `G4track` is a distinct, lower-level library.

## Measurement

Natural silicon, nine projectile species, nine momenta (0.05–100 GeV/c, including
4/5/6 GeV/c transition points), 512 samples per nonzero-rate point. One point has
zero rate: 40960 interactions from 41472 requests. Three forward runs per worker
count plus reverse-order checks at one/eight workers. Same event seeds and work
at all worker counts. No sampling warm-up; initialization and CSV writing are
outside sampling times. Apple M3 Pro, 12 CPU cores, 18 GiB RAM.

| Workers | Median wall s | Total CPU s | Speedup | Peak RSS MiB |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 6.941 | 6.924 | 1.00 | 72.73 |
| 2 | 3.546 | 7.063 | 1.96 | 74.45 |
| 4 | 1.818 | 7.203 | 3.82 | 77.66 |
| 8 | 1.123 | 8.863 | 6.18 | 83.88 |

These are **isolated interaction-generation timings**, including validation/RNG
accounting and retaining products. They do not measure full Fatras throughput.
Median setup is about 0.05 s. Eight workers use 28% more total CPU than one worker;
wall time falls by 84%. No claim of linear scaling beyond the measured range.

- All event, product and rate CSVs are byte-identical across all 14 runs,
  including reversed work order. Stored per-event hashes cover particle IDs,
  masses, charges, momentum components, target, rate, deposited energy and status.
- Reference: existing serial Geant4 process adapter on the same momentum grid,
  with matched G4 projectile masses and independent seeds, 512 samples/point.
  Maximum relative rate difference is 4.25e-12 (12-digit reference output).
- Across 80 nonzero-rate points, multiplicity, charged multiplicity and leading
  energy show a largest mean difference of 2.72 combined SEM among 240 comparisons.
  This is a descriptive check, not proof of model equivalence. PDFs also compare
  daughter momentum and angular distributions at 2 GeV/c without momentum cuts.
- The probe retains G4's model-overlap selector, cross-section-weighted target
  sampling, frame rotation, nominal-mass projection and neutral-kaon conversion.
  There are 367 mass projections in the sample. Nuclear fragments are recorded
  explicitly; nonnuclear comparison plots omit them as the ACTS adapter folds them
  into an untransported residual. No strict final-state conservation is imposed
  by rejecting interactions; intrinsic model residuals remain diagnostic data.
- AddressSanitizer and ThreadSanitizer probe builds each finish 5120 interactions
  on eight workers without reported errors. **G4 libraries are uninstrumented**:
  this is not a complete race/memory-safety proof inside G4.

## Reproduce

Use an MT-enabled Geant4 environment and its dataset environment variables:

```sh
python build.py --geant4-config /path/to/geant4-config --output /tmp/direct-model
python run.py --executable /tmp/direct-model --output /tmp/direct-scan
python build-reference.py --acts-source /path/to/fatras-compact \
  --acts-build /path/to/existing-build --geant4-lib /path/to/lib \
  --output /tmp/process-reference
mkdir -p /tmp/process-reference-results
/tmp/process-reference /tmp/process-reference-results 512
python compare.py --scan /tmp/direct-scan \
  --reference /tmp/process-reference-results --output /tmp/direct-report
```

`build-reference.py` uses the parent package's existing macOS ACTS bridge build
helper, and requires the optional on-demand backend. It explicitly aligns
projectile masses to isolate component differences from ACTS/G4 mass conventions.
`build.py --sanitizer address` or `--sanitizer thread` instruments the probe only.
Plotting requires numpy and matplotlib. The runner retains one compressed set
of all outputs and SHA256 hashes for every run; mismatches preserve their CSVs.

Results: `../results/2026-10-15/direct-model/`. The archive contains the PDF,
summary, complete compressed baseline/reference outputs, all run reports,
compiler commands, source hashes, dependency audit and sanitizer logs.

## Production gates

- Integrate context lifetime with ACTS's worker pool; do not create models per
  event. The probe uses independent `std::thread` workers, not the ACTS sequencer.
- Preserve full process semantics, including rare rejected model results and
  zero-energy surviving primaries; the probe records catastrophic energy cases
  (zero observed) instead of implementing the process's retry policy.
- Establish safe registry ownership/teardown and compatibility with other Geant4
  users in one process. Probe registry cleanup is only valid in its isolated job.
- Repeat concurrency checks with instrumented G4 libraries, broader targets,
  worker reuse and supported G4 versions before claiming general thread safety.
- Repeat the inclusive ODD comparison and full-event throughput benchmark after
  integration. This probe neither closes the hit deficit nor changes navigation.
