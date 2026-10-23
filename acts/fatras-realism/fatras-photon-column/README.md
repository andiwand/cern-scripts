# Sampled photon birth-column transport

Validate ACTS `ae02eeb5fb` on `fix/fatras-radiative-secondaries`. The production
change retains explicit bremsstrahlung and outgoing Compton photon depths and
transports them through the remaining birth column before navigation. Conversion
daughters keep their existing treatment. Charged Compton recoils and ionisation
daughters remain thin-slab approximations; geometry is unchanged.

## Experiments

- Thirteen matched-material slab settings, 100,000 incident particles each.
  Si/Cu, 30 mm, common EM or full scattering profile; 1/20/1000 cells.
  Same materials and 100 keV diagnostic production cuts as
  [the original slab tests](../fatras-slab-validation/README.md).
  Reference means and errors come from that immutable archive. These cuts
  belong to the controlled experiment, not the inclusive hit summaries.
- Three identical ttbar + fixed PU200 events, seed 42, 2 T, cached/pruned 5 mm
  low-momentum transport, p >= 0.2 MeV and pT >= 0.05 MeV; photons and production
  thresholds 100 keV. All written hits enter the summary without analysis cuts.
  Compare genuine pinned ACTS main `300b664a3d`, changed Fatras and default
  FTFP_BERT G4 physically confined to r <= 1202 mm, |z| <= 4002 mm.
- Alternate the accepted `5825d58880` module and current module in serial fresh
  processes, three repeats each. CPU is sequencer user+system time, including
  CSV I/O and lazy physics initialization, excluding geometry setup. Main CPU
  is the archived five-event measurement; G4 is the same-day archived three-event
  measurement. Neither is represented as a fresh timing in this experiment.
- Confirm exact CSV replay within each variant, the control against accepted
  `5825` output, and standard-navigation one/four-worker equality. Low-momentum
  navigation remains a one-worker validation prototype; this change adds no
  worker restriction or G4 dependency to native EM physics.

## Reproduce

Use a fresh `WORK` directory. `run-env.sh` invokes Python itself. Do not rebuild
the frozen installed ACTS tree; builders compile current kernels and the
established validation bridge against its d25514208b ABI.

```sh
../fatras-neutral-hadrons/odd/run-env.sh ../fatras-slab-validation/build.py --source SOURCE --work WORK/slab-build
../fatras-neutral-hadrons/odd/run-env.sh slabs.py --work WORK
../fatras-neutral-hadrons/odd/run-env.sh ../fatras-radiative-secondaries/build.py --source SOURCE --work WORK/runtime-build
# Finish all builds/slab tests before the serial CPU experiment.
python inclusive.py --source SOURCE --work WORK
python analyse.py --work WORK
python plot.py --work WORK --output WORK/photon-column.pdf --preview
```

The control runner initially records its current source checkout even though it
loads an archived binary. Analysis preserves that as `runner_checkout_revision`,
records the binary's actual source revision, and verifies its event hashes against
the accepted archive. Module hashes, build commands, input/material metadata,
source snapshots and hashes are retained. `archive.py` stores one compressed event
sample and hashes for repeated samples. All archives are optional validation
outputs; none is a shipped physics input.

`results/2026-10-16/photon-column.pdf` contains inclusive counts/CPU, regional and
process comparisons, and slab controls. Results do not establish material/physics
fractions for the detector-wide gap. Annihilation, charged-daughter material and
subdivision-sensitive scattering remain separate work; many thin slices are not
an acceptable production replacement.

## Measured result — 16 October 2026

- Secondary ID hits/event: 95,749.7 -> 97,091.0, versus G4 114,198.3;
  deficit 16.15% -> 14.98%. Pixel deficit 8.14% -> 7.56%.
- Native direct-Compton hits/event: 1,594 -> 2,025. Retained truth grows
  421,302 -> 555,149 particles/event (+31.8%).
- CPU median: 11.605 -> 14.314 s/event (+23.3%). The modest +1.40% secondary
  hit gain does not justify calling the occupancy/CPU problem solved.
- Failed propagations rise from 9 to 27 across the three events, all at the
  existing next-target-call limit. Their output is excluded by the simulator;
  no extra analysis cut hides them. Navigation is unchanged.
- One-slab 1 MeV photon Compton yield in 30 mm Si: 0.31458 -> 0.42895,
  G4 0.43264. Changed 1,000-slice result 0.42884. Charged escape remains wrong
  until recoil/ionisation daughter material is handled consistently.
