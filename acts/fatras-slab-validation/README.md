# Matched-material Fatras / Geant4 slab response

Quantify EM interaction and within-material transport errors without ODD material
placement. This is an external diagnostic, not a new Fatras transport backend.
ACTS source remains at `5825d58880` on `fix/fatras-radiative-secondaries`.

## What is compared

- Normally incident photons (0.2, 1, 5, 20 MeV) and electrons (1, 5, 20 MeV),
  zero field, Si/Cu slabs 0.3, 3 or 30 mm thick. Geant4's slab has 50 m transverse
  half-width; Fatras uses planar cells without lateral boundaries. These are
  bulk-slab controls, not sensor models or predictions of detector occupancy.
- Both use the same NIST material density, effective A/Z, X0, L0 and mean
  excitation energy. The native input explicitly takes G4's excitation energy;
  residual density-effect, stopping and atomic-physics approximations remain
  differences in the models.
- Electron/positron and photon production cuts correspond to **100 keV**.
  G4 range cuts are obtained by inverting its range-to-energy converters; the
  actual post-initialization cut table is checked in every run. Counts and
  escaping kinetic energy are scored above 100 keV. Photons below 100 keV are
  removed in both simulations; charged particles continue to stopping. There
  are no charged momentum, transverse-momentum or time cuts in this experiment.
- G4 uses `G4EmStandardPhysics`, with individually exposed photon processes.
  No hadronic physics is included. This is a deliberately controlled EM
  experiment: **the inclusive, default FTFP_BERT ODD ID reference is unchanged**.
- `primary` records secondary production but kills daughters; the outgoing
  Compton photon continues the incident photon history in both implementations.
  `cascade` transports all retained descendants. Conversion counts are numbers
  of produced electrons/positrons above threshold, not numbers of pairs.
- Production means and standard errors are accumulated per incident event,
  including all its descendants. Escape counts include primary particles.
  `primary_exit_MeV` is zero for a stopped/converted primary. `compton_scatter`
  counts recoils at all energies; `compton` counts those above 100 keV.

| Profile | G4 processes | Native processes |
| --- | --- | --- |
| common | ionisation, brems, conversion, Compton | same families |
| photoelectric | common + photoelectric | not used |
| annihilation | common + positron annihilation | not used |
| extended | common + photoelectric + annihilation | not used |
| full | standard EM including multiple scattering | common + current scattering |

Multiple scattering is off except in `full`. All profiles share material and
production thresholds. Profile differences are controlled causal experiments,
not components to add to the ODD hit deficit.

## Native slab approximation

The harness invokes the production `SimulationActor::interact`, charged
scattering/interleaved-ionisation-and-brems list, and photon conversion/Compton
list. It retains conversion daughters' sampled remaining column. Other daughters
skip the rest of their birth cell, exactly the current production limitation.
A scattered photon preserves its incident-history status for primary-only
scoring. No custom cross section, production multiplier or loss formula is used.

A particle consumes a planar cell with its incident-direction path correction;
its outgoing direction chooses the next cell. Cell boundaries provide straight
free flight without magnetic navigation. Within-cell spatial displacement and
multiple-scattering path changes remain unresolved, as in the surface model.
Subdividing the **same total material** tests this approximation. Rare pathological
cascades would throw at the explicit work limits instead of silently truncating;
all accepted runs complete.

The 100/1000/10000-slice full-profile runs are sensitivity tests, **not a
converged transport solution**. The electron branch of the production scattering
width uses Rossi–Greisen with a logarithmic thickness correction. Applying it
independently to increasingly small pieces changes the total angular variance.
Energy-loss/scattering ordering and spatial transport also change with slicing.
Do not choose a slice count because one observable happens to match G4.

## Results and reproduction

`results/2026-10-16/slab-validation.pdf` contains four pages. The scan has 232
settings at 10,000 trials each; 40 refined settings use 100,000 trials; four
process-attribution settings use 100,000 and one 10000-slice setting uses 20,000.
Total: **277 settings / 6,740,000 primary trials**. Mean/standard-error CSVs,
commands, seeds, logs and binary hashes are retained for every setting.

Run through `../fatras-neutral-hadrons/odd/run-env.sh` to load the established
local ACTS/Geant4 environment (the wrapper invokes Python itself):

```sh
../fatras-neutral-hadrons/odd/run-env.sh build.py --source SOURCE --work WORK
../fatras-neutral-hadrons/odd/run-env.sh run.py --work WORK
python analyse.py --work WORK
python plot.py --work WORK --output WORK/slab-validation.pdf --preview
../fatras-neutral-hadrons/odd/run-env.sh verify.py --work WORK --binary WORK/slab
```

`run.py --phase scan|refined|attribution` selects a stage. Existing completed
records are preserved; use a fresh directory for a changed model. The builder
extracts compiler/dependency flags from the installed build's compile database
and compiles the selected current native physics sources. It does not rebuild
the frozen d25514208b installation. The linked Core scattering implementation
is unchanged between that build and the selected ACTS source.

Results demonstrate sizeable cascade/escape errors at identical material, a
roughly 31% annihilation contribution to Compton yield in one photon-beam test,
and a strong scattering subdivision sensitivity. Smaller kernel differences
remain, including roughly 10% deficient conversion-daughter yield for 5 MeV
photons in 30 mm copper. **These tests cannot assign percentages of the ODD
16.15% secondary-hit deficit to physics versus material placement.** The actual
ODD source spectra, locations, angles and sensor response remain necessary.

No production change, runtime table, geometry edit or new shipped data follows
from this diagnostic. Validation archives are optional local outputs.
