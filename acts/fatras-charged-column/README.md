# Charged secondary birth-material transport

Validate ACTS `120acbe04e` (physics) and `9f0c238086` (pre-propagation
navigation-cache fix) on `fix/fatras-radiative-secondaries`. Geometry is unchanged.
Ionisation and Compton recoil electrons consume their remaining birth columns;
local electron scattering power and bounded energy/angular steps resolve
stopping and direction changes without thousands of material slices or new
runtime physics files. See the ACTS `fatras_electron_transport.md` documentation.

## Experiments

- 34 homogeneous Si slab settings, 50,000 incident particles each (1.7 million
  trials). Common processes, common plus scattering (`transport`), and full G4
  EM; 1/20 MeV electrons and photons. Thick 30 mm cascades, thin 0.3 mm angular
  checks, 1/1000-slice and tightened-step controls. All use identical material
  and 100 keV diagnostic thresholds. `primary_exit_sin2`, `primary_exit_cosine`
  and `primary_exit_MeV` are unconditional means, with zero for stopped
  primaries; `primary_escape` gives the survival fraction. These cuts apply
  only to controlled diagnostics.
- Same three ttbar + fixed PU200 events, seed 42, 2 T. All written ID hits;
  no summary p/pT or time cuts. Fatras p >= 0.2 MeV, pT >= 0.05 MeV, production
  and photon acceptance 100 keV. Cached/pruned 5 mm navigation, four-turn and
  50,000-step limits. Default FTFP_BERT G4 remains physically confined to
  r <= 1202 mm, |z| <= 4002 mm, with no added particle cuts.
- Summary baseline is genuine ACTS main `300b664a3d`. The accepted ae02 Fatras
  module is a separate timing/physics control. Three serial fresh-process
  repeats per variant; CPU includes sequencer initialization, simulation and
  CSV writing, excluding geometry setup. Main CPU is the archived five-event
  measurement; G4 CPU is the archived same-day measurement, not a fresh run.
- Ablations: ae02 physics plus only the Core cache fix; new adaptive/scattering
  physics with ionisation and Compton-electron birth records omitted. These
  distinguish birth absorption from a scattering-driven hit reduction.
- Exact CSV equality across repeats, archived-control replay and standard
  navigation with one/four workers. Low-p navigation remains a one-worker
  validation prototype; native EM physics adds no threading dependency.

## Reproduce

Use a fresh `WORK`; the runners refuse overwriting outputs. Builders compile
current sources against the frozen d25514208b validation ABI. Do not rebuild
that installed tree. `run-env.sh` invokes Python itself.

```sh
../fatras-neutral-hadrons/odd/run-env.sh ../fatras-slab-validation/build.py --source SOURCE --work WORK/final-slab-build
../fatras-neutral-hadrons/odd/run-env.sh slabs.py --work WORK
../fatras-neutral-hadrons/odd/run-env.sh ../fatras-radiative-secondaries/build.py --source SOURCE --work WORK/runtime-build
../fatras-neutral-hadrons/odd/run-env.sh ablate.py --source SOURCE --work WORK
# Complete all other computation before measuring serial CPU.
python inclusive.py --source SOURCE --work WORK
python analyse.py --work WORK
python plot.py --work WORK --output WORK/charged-column.pdf --preview
python archive.py --source SOURCE --work WORK --output results/2026-10-16
```

Analysis records the archived control binary's actual revision separately from
its runner checkout and verifies exact replay hashes. Build commands, source
snapshots, module/data hashes and logs are archived with the PDF. One compressed
inclusive event sample is retained; repeated samples have hashes. Results are
local ignored validation artifacts, not runtime inputs or shipped tables.

The Core regression fails on the original propagator and passes with the fix,
checking both forward/backward initial navigation after a pre-propagation actor
changes the stepper. 209 Fatras cases pass, including ordered daughter depths,
independent scattering quadrature, soft stopping bounds and process vetoes.
Repository pre-commit checks pass. The frozen-library validation is not a full
clean rebuild of all ACTS examples.

## Measured result — 16 October 2026

- Secondary ID: 97091.0 -> 82925.7/event, G4 114198.3; deficit grows from
  14.98% to 27.38%. Pixel: 35760.3 -> 28405.0, G4 38683.3, deficit 26.57%.
- New integration/scattering without the new charged birth columns gives
  97737.7 ID hits/event. Adding them removes 14812, mainly ionisation carriers.
  Slab escape improves from 6.2537 to 0.98632 without scattering, G4 1.00224;
  retaining false escape would conceal missing response.
- Fresh CPU median 15.199 -> 19.752 s/event (+29.95%); archived main 0.790,
  G4 39.285. This is a correctness change with a cost, not an occupancy or
  performance closure. Retained truth grows to 585623 particles/event.
- Final failures: 27 control, 7 Core-only, 2 full change; count particle error
  lines once, excluding the aggregate log summary. Two step-limit failures
  remain visible. Exact repeat/control/thread replay checks pass.
- Geometry remains deferred. Next physics priority is native positron
  annihilation, including stopped positrons; its inclusive gain is unmeasured.
