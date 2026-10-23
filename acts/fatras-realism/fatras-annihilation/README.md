# Native positron annihilation validation

Current ACTS commits `4f7b29cef6` and `41298a4018` on `fix/fatras-radiative-secondaries`. No new runtime table or G4 EM/threading dependency. The frozen installed ACTS ABI is intentionally not rebuilt.

Three inclusive ttbar + fixed PU200 events: 83601.7 secondary ID hits/event versus 114198.3 default ID-confined G4; 28344.3 secondary pixel hits versus 38683.3. The annihilation toggle adds 676 ID hits/event (+0.82%); matched CPU median rises from 18.224 to 19.437 s/event (+6.65%). Summary baseline is ACTS main `300b664a3d`, not the preceding changed implementation.

Artifacts: `results/2026-10-16/annihilation.pdf`, `analysis.json`, `attribution.json`, `checks.json`, `inventory.json`. The local archive contains compressed event evidence; it is not a simulation input or part of the code commit.

## Reproduce

Use a new work directory. The CPU driver alternates three serial repeats per variant; do not run other CPU-intensive diagnostics concurrently. Standard-navigation one/four-worker replay is separate from the one-worker cached low-p navigation prototype.

```sh
fatras_tools="$HOME/cern/scripts/acts"
fatras_source="$HOME/cern/source/acts/acts/fatras-soft"
validation_work="/private/tmp/fatras-annihilation-replay"
python3 "$fatras_tools/fatras-radiative-secondaries/build.py" --source "$fatras_source" --work "$validation_work/runtime-build"
"$fatras_tools/fatras-neutral-hadrons/odd/run-env.sh" "$fatras_tools/fatras-slab-validation/build.py" --source "$fatras_source" --work "$validation_work/slab-build"
"$fatras_tools/fatras-neutral-hadrons/odd/run-env.sh" "$fatras_tools/fatras-annihilation/slabs.py" --work "$validation_work"
"$fatras_tools/fatras-neutral-hadrons/odd/run-env.sh" "$fatras_tools/fatras-annihilation/kernel.py" --work "$validation_work"
python3 "$fatras_tools/fatras-annihilation/inclusive.py" --source "$fatras_source" --work "$validation_work"
python3 "$fatras_tools/fatras-annihilation/analyse.py" --work "$validation_work"
python3 "$fatras_tools/fatras-annihilation/attribute.py" --work "$validation_work"
/private/tmp/fatras-runtime-work/venv/bin/python "$fatras_tools/fatras-annihilation/plot.py" --work "$validation_work" --output "$validation_work/annihilation.pdf"
python3 "$fatras_tools/fatras-annihilation/archive.py" --source "$fatras_source" --work "$validation_work" --output "$fatras_tools/fatras-annihilation/results/NEW_DATE"
```

Dependencies: the existing runtime-model input sample, frozen build and G4 installation/data, accepted charged-column module and inclusive analysis, immutable default-G4 CSVs, and the observational G4 process/location record. `run-env.sh` supplies the installed G4 environment; even the standalone direct G4 kernel needs it.

## Interpret the evidence

- `slabs.py`: matched native/G4 scattering and annihilation toggles, plus full G4; 20000 primaries/setting. Only these diagnostics use common 100 keV thresholds. ODD G4 remains default/inclusive.
- `kernel.py`: total rate and photon energy-sharing check. Rates agree within 0.13 ppm; installed G4's isotropic CM final-state construction differs from the native analytic PRM prescription at high energy. This is explicitly retained, not tuned away.
- `analyse.py`: all written hits, regional/process partitions and CPU; repeated event hashes, exact disabled-process replay, worker equality and physical ID-world assertion.
- `attribute.py`: complete available truth ancestry, annihilation pairs and descendants, ionisation sources/hits above a common 2 MeV diagnostic energy, native Compton photon-source ancestry, G4 observed creation process/location. Native continuation photons are not new annihilation sources. G4 Other includes photoelectrons; do not equate it with Compton.
- `plot.py`: seven-page PDF with inclusive ACTS-main/changed/G4 comparison, process/region differences, annihilation lineage, residual budgets, source counts, controlled slabs and kernel comparison.
- Two maximum-step failures remain per three events. Current source is exercised through the established frozen-ABI bridge, not a full clean installed-tree build.

The largest residual is ionisation-carrier response (18815 missing ID hits/event), followed by conversion (7884), partly hidden by 5004 excess nuclear hits. Material placement remains deferred. Above 2 MeV, retained ionisation sources reach 80.9% of G4 but their hits only 27.9%; source production alone does not describe the response gap. Do not interpret overlapping process, energy and birth-location diagnostics as additive causal corrections.
