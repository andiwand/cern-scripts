# Inclusive secondary-hit diagnosis

Reuses the accepted optimised **numerical** Fatras archive and the default,
physically ID-confined Geant4 reference. No experimental helix reference and no
analysis momentum/time cuts. Three matched ttbar + fixed PU200 events, 2 T.

- `analyse.py`: process, detector volume, PDG, ancestry, momentum, time,
  birth-distance and unique carrier/sensor accounting. All secondary hits are
  partitioned, including underflow and overflow; totals are asserted.
- `revisits.py`: independent time-ordered audit of repeated carrier/sensor visits.
- `carriers.py`: retained truth versus particles with hits, by parent and energy.
  Retained truth is **not** an unbiased produced-particle count in Fatras.
- `sensitivity.py`: unchanged-physics runs with different numerical step/turn
  budgets. Uses the existing cached/pruned bridge from
  `../fatras-transport-performance/`; refuses output overwrites.
- `plot.py`: five-page PDF; includes pinned ACTS main, changed Fatras and Geant4
  totals/CPU. Detailed attribution uses the latter two archived CSV samples.
- `archive.py`: compresses new validation outputs and hashes all archived files;
  does not duplicate existing reference event data or introduce runtime inputs.

Example (Python with NumPy/Matplotlib for plotting; analysis uses standard library):

```sh
python analyse.py \
  --run Fatras ../fatras-transport-performance/results/2026-10-16/pruned-check \
  --run Geant4 ../fatras-soft-secondaries/results/2026-10-15/geant4 \
  --output WORK/summary.json
python revisits.py --summary WORK/summary.json --output WORK/revisits.json
python carriers.py --summary WORK/summary.json --output WORK/carriers.json
python sensitivity.py --output WORK/runs \
  --source ~/cern/source/acts/acts/fatras-soft \
  --module /private/tmp/fatras-transport-work/pruned-build
python sensitivity.py --output WORK/runs \
  --source ~/cern/source/acts/acts/fatras-soft \
  --module /private/tmp/fatras-transport-work/pruned-build --variant loops16 5 16
python analyse.py --run loops8 WORK/runs/loops8 --run step2p5 WORK/runs/step2p5 \
  --output WORK/sensitivity.json
python analyse.py --run loops16 WORK/runs/loops16 --output WORK/loops16.json
python plot.py --work WORK \
  --reference ../fatras-transport-performance/results/2026-10-16/summary.json \
  --output WORK/secondary_gap.pdf
```

The module is built at source `d419e58b19705e27081e9c718f7c9ead9ddf6f98`
using the earlier frozen-build validation bridge. Its hash and build description
are in each sensitivity metadata file. The recorded commands and source hashes
allow the temporary build to be recreated using the transport-performance tools.
No ACTS default or physics implementation is changed by this study.

Definitions: secondary = full barcode generation > 0; pixel volumes 16/17/18;
strip volumes 23/24/25/28/29/30; barrels 17/24/29. CSV particle accessors expose
initial state (birth for secondaries); times are mm/c and converted to ns.
Repeated visits = hits minus unique (particle barcode, geometry ID) pairs per
event. This is not a digitized-channel occupancy estimate. Birth distance is
Euclidean displacement, not track length or evidence of birth inside a sensor.
Ancestry uses complete barcode tuples and checks for cycles.

Process labels are the carrier's birth process. Nuclear π0 photons have folded
nuclear tags in Fatras; combine nuclear/decay photon origins when interpreting
conversion genealogy. Geant4 `Other` does not retain the exact process subtype.
Production cuts differ: 100 keV fixed ionisation threshold in Fatras versus
Geant4's default material-dependent range-to-energy conversion; G4 is unchanged.

Results: `results/2026-10-16/secondary_gap.pdf` and the adjacent JSON files.
Small sample; physics random histories diverge when transport changes. Sensitivity
runs are not matched-hit recovery estimates and do not establish convergence.
CPU is process user+system including CSV output; new timings are single runs,
whereas the accepted numerical reference uses the earlier repeated median.
