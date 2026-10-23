# Fatras validation

Standalone checks for the ACTS Fatras foundation changes, 2026-10-13.
These are development tools, not an ACTS Examples writer or physics parametrisation.

## Run

Use an ACTS build of the source checkout with Fatras, integration tests and
`CMAKE_EXPORT_COMPILE_COMMANDS` enabled. Build `ActsIntegrationTestFatrasSimulation`
first. The runner reuses that target's compiler flags and built libraries.

```sh
python3 run.py \
  --source ~/cern/source/acts/acts/dev3 \
  --build /private/tmp/acts-atlas-review-build \
  --output /private/tmp/my-fatras-scan \
  --events 10000 --repeats 3 \
  --cuts 0.05 0.1 0.5 --pt-cuts 0 0.05 0.1
```

Cuts are in GeV; use a new output directory. This diagnostic requires pMin >=
50 MeV. Production Fatras has no such imposed floor. `--first-event` isolates an
input event; `FATRAS_TRACE=1` enables verbose propagator/navigation logs on stderr.
Timing with tracing enabled is not representative.

The sample contains eight primaries per event: electrons, positrons, two photons,
charged pions and muons. Momentum is log-uniform from 0.1 to 10 GeV, eta uniform
from -1 to 1, phi uniform. A fixed 2 T z field and the test helper's four-layer
cylindrical silicon geometry are used. Charged EM processes and neutral photon
conversion match the Examples configuration; there are no decays or hadronic
interactions. Charged pT cuts apply at entry and during transport; neutral
selection uses p only. Independent generation and transport RNG streams keep
input particles identical across cuts. Changed interactions/selections can change
later transport RNG consumption within an event.

Results contain transport wall time, event median/p95, primary rejections,
particle/hit counts, secondary counts by process and layer occupancy, and failure
counts by error. Log files include failed particle initial states. Geometry
construction, compilation and input generation are outside timing; the first
transport call is included. These are small wall-time measurements, not a
production CPU benchmark. Rejected daughter counts and process-level rejection
reasons are not instrumented. `killed_particles` counts final particles with
`Particle::isAlive()==false`, not every transport termination.

Optional `--compare-ref REV` overlays historical Fatras headers while using the
same built libraries. Historical runs only support pTMin=0. This is useful for
the header-only default-EM fixes against the recorded base revision. It is NOT a
full historical build or a Geant4 comparison, and must not be used if headers and
libraries have incompatible APIs/ABIs. The script records revisions, library and
source hashes, build commands, source snapshots and the Fatras diff. Rebuild the
ACTS libraries after changing compiled sources.

## Recorded checks

`results/2026-10-13/` contains:

- `p-scan/`: 10,000 events, three repeats per cut, current vs base headers
  (`300b664a3d9c32ec928208e7eb18df40e7b2721b`), before adding the optional pT cut.
- `pt-scan/`: 10,000 events, three repeats, pMin=50 MeV and three pT thresholds.
- `checks/`: Fatras unit and integration test logs, syntax checks for the Examples
  algorithm and Python binding, and repository pre-commit checks.
- `implementation.patch`: the ACTS changes, including new regression tests.

At pMin=50 MeV:

| Charged pTMin | All hits | Secondary hits | Failed particles |
| --- | ---: | ---: | ---: |
| disabled | 315186 | 1818 | 2 |
| 50 MeV | 315087 | 1807 | 2 |
| 100 MeV | 301641 | 1619 | 0 |

At pMin=100 and 500 MeV with pTMin disabled, the earlier scan has 1602 and 970
secondary hits respectively, and zero failures. The foundation fixes preserve
secondary-hit counts in that sample; lower cuts expose additional existing EM
secondaries. No hadronic improvement is claimed.

The failures at pMin=50 MeV occur at events 1622 and 7951 (seed 42), for primary
electrons. Event 1622's verbose trace shows finite ~5 mm steps around a roughly
12 cm radius orbit before the 1000-step limit. The initial half-turn path allowance
is about 7.06 m; the electron loses energy during transport, while the allowance
is based on the starting momentum. This is evidence of curling exhausting the
step budget, not proof of a universal curvature threshold. Failed trajectories
lose their accumulated hits in MultiParticleSimulation. A pT cut is an acceptance
and cost choice, not a demonstrated navigation repair; it remains disabled by
default.

For a singly charged particle in a uniform axial field,
`R[m] = pT[GeV] / (0.299792458 B[T])`. A global-z pT cut is therefore a radius cut
only for that field orientation and fixed charge magnitude. A local curvature
cut in arbitrary fields requires a separate definition.

All 24 Fatras unit-test executables and 257 integration cases (19079 assertions)
pass. The optional Geant4 decay test needs the Geant4 ENSDF dataset, e.g.:

```sh
G4ENSDFSTATEDATA=~/cern/install/geant4/11.3.1/share/Geant4/data/G4ENSDFSTATE3.0 \
  ctest --test-dir /private/tmp/acts-atlas-review-build -R '^Fatras' --output-on-failure
```

The Examples algorithm and Python binding translation units passed syntax checks
using the existing full build's flags. The Python extension was not rebuilt or
runtime-tested. Full detector/reference-physics validation is still needed before
choosing production cuts or judging agreement with full simulation.
