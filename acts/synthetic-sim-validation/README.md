# Validating the ACTS synthetic space point generator

`ActsFatras::Synthetic` is a deliberately coarse fast simulation that produces
space point events for seeding benchmarks. These scripts check that its
distributions are in the right place, which is the only claim it makes. Two of
its three shipped layouts have a full simulation to be checked against: the ITk
against a GNN4ITk Athena dump, the ODD against ColliderML.

## Running it

```sh
# fast-simulation events per layout, one CSV pair each
python3 dump_fastsim.py itk -o /tmp/fastsim-itk --events 50
python3 dump_fastsim.py odd -o /tmp/fastsim-odd --events 50

# ITk, against a local GNN4ITk dump, on the events the fit did not see
./validate.py itk --fullsim '~/Downloads/user.avallier.*.DumpGNNITk_v9.root' \
    --fastsim /tmp/fastsim-itk --events 250 --skip-events 250

# ODD, against ColliderML ttbar at a pile-up of 200; the shard is downloaded
# from HuggingFace on first use and cached
./validate.py odd --fastsim /tmp/fastsim-odd --events 50 --skip-events 50
```

Plots land in `~/cern/data/synthetic-sim-validation/plots/<detector>/` as PDF
(`-o` elsewhere), so the two comparisons do not overwrite each other; `--format png` for a raster. Everything is normalised per event, so
the samples are comparable whatever number of events each holds - but give
`dump_fastsim.py` as many events as the reference has, or the fast-simulation
line carries several times the noise of the line it is read against.
`fastsim.load` globs the prefix, so clear the old CSVs before a shorter run.
The reduced references (`sample-*.npz`, `target-*.pkl`) are cached in
`~/cern/data/synthetic-sim-validation` (`--cache-dir`).

`dump_fastsim.py` generates from the shipped files through the Python bindings;
`ActsBenchmarkSyntheticEventGeneration --layout itk --dump <prefix>` writes the
same two files faster, where the benchmark is built.

The two shipped configurations came out of

```sh
./fit_event_config.py itk --fullsim '<dump>*.root' --events 250 \
    --path-length 4 --turns 3 --set secondaryKt=0.319 \
    --set stubRate=1.267 --set stubClusters=2.1 --set stubReach=4.0
./fit_event_config.py odd --events 50 --path-length 4 --turns 3 \
    --set secondaryKt=0.319 \
    --set stubRate=1.800 --set stubClusters=2.1 --set stubReach=4.0
```

which write `itk-ttbar-pu200.json` and `odd-ttbar-pu200.json` into
`Fatras/data`; `--out <prefix>` writes them somewhere else and `--out -` writes
nothing. Every field is stated in the file, so a change to a default cannot
retune one. The two halves are
disjoint and the validation gets the same number the fit did: `--events N` takes
the front of each ITk file and of the ODD shard, `--events N --skip-events N` in
`validate.py` takes what follows. The ITk splits its five hundred events 250/250
- at fifty a half its two halves differed by a flat 5 %, which was the whole of
its apparent deficit. The ODD shard holds a hundred and cannot. The stub
channel and the kick are passed in because they are measured elsewhere and this
fit does not touch them; left out they would silently go to zero and to the
fit's own answer. The fit is deterministic - rerunning it on the same reference
reproduces the parameters bit for bit - so repeat it only when something
upstream has changed.

### The ODD path needs pyarrow, which the ACTS environment breaks

ColliderML is Parquet, which needs `pyarrow` (`uproot`, `numpy` and `matplotlib`
are in `requirements.txt`). In the ACTS spack environment importing it fails on a
missing `_iconv`: spack's `libiconv` shadows the macOS one the wheel was built
against. Dropping spack's library paths for the run is enough:

```sh
env -u DYLD_LIBRARY_PATH -u DYLD_FALLBACK_LIBRARY_PATH ./validate.py odd ...
```

This is the same breakage that makes `awkward` unusable there, which is why the
ITk loader asks uproot for `library="np"`.

## The scripts

| | |
| --- | --- |
| `presets.py` | the shipped detectors and configurations as files, and the flat field names the fit talks in |
| `sample.py` | the `Sample` every loader produces and `validate.py` plots |
| `fullsim_itk.py`, `fullsim_colliderml.py`, `fastsim.py` | one loader per sample format, so a third full simulation means one more file |
| `dump_fastsim.py` | generate an event from the shipped files and write the CSV pair |
| `validate.py` | the comparison and its plots |
| `scorecard.py` | the scored figures for a shipped configuration, in a minute |
| `fit_event_config.py` | fit `EventConfig` to a reference and write it as JSON |
| `ablate.py` | remove one term of the model at a time and score what is left |
| `itk_layout_from_xml.py` | the ITk description, out of the ATLAS GeoModelXml |
| `layout_from_geometry.py` | the ODD and Generic descriptions, out of the ACTS geometry |
| `material_from_geometry.py` | the material half of the same, matched onto a shipped description |
| `material_budget.py` | what a ray collects in a shipped detector, against the geometry it was read from |
| `measure_secondary_kinematics.py` | the secondary momentum and kick laws, off the dump's parent links |
| `measure_secondary_populations.py` | the same on ColliderML, which has no truth-link threshold; also the stub channel |
| `measure_overlaps.py` | module overlap, off the dump's own module identifiers |
| `implied_material.py` | what material profile the reference asks for, cell by cell in (r, \|z\|) |
| `reference_scatter.py` | whether a mismatch is the model or the reference's own noise |

The first seven are the pipeline; the rest each answer a question the fit cannot,
and each produced a number that is now pinned in a preset rather than fitted.

### Descriptions and material are read, not fitted

A geometry is a known thing and should not be fitted to simulated data. Each
shipped detector is read out of the authoritative description of that detector
and written into `Fatras/data` as three files sharing a prefix: the description
(where its layers are), the material (what they are made of) and the
configuration fitted to it. `--out <prefix>` writes them somewhere else, which is
what to do before overwriting what ships.

```sh
# the ITk, out of the official GeoModelXml. Needs a CERN account.
git clone ssh://git@gitlab.cern.ch:7999/Atlas-Inner-Tracking/ITKLayouts.git
python itk_layout_from_xml.py ITKLayouts            # --report for the sections

# the ODD and the Generic detector, out of the geometry ACTS builds for them
python layout_from_geometry.py odd
python layout_from_geometry.py generic --report

# the material of any of them, including the ITk's, matched onto the layers of
# the description it is written beside
python material_from_geometry.py itk

# and what the result collects along a ray, against the geometry it came from
python material_budget.py itk
```

`layout_from_geometry.py` is just `makeDescriptionFromTrackingGeometry`, so for a
detector ACTS can build there is nothing to transcribe, and
`Python/Examples/tests/test_fatras_synthetic_layout.py` checks that the shipped
files still match the geometry. It folds the two endcaps the reduction measures
into one mirrored one where they agree, which is what makes the file half the
size; `--no-mirror` keeps both. The ITk has no ACTS geometry to reduce
wholesale, hence the XML for its positions and `material_from_geometry.py` -
which builds `acts.examples.itk` - for its material. Run these with
`python <script>`, not the shebang: the shebang picks up a different interpreter
and DD4hep then fails to find its plugins.

A surface does not carry one slab. It is banded along itself - `r` on a disc,
`|z|` on a cylinder - so that a ring is told from the gap beside it and the
barrel end of a service cylinder from its endcap end. Each band carries a
*material* of its own at a thickness they all share, rather than a thickness of
its own at a shared material: both hold the same two numbers, but only the first
lets `L0/X0` be read off and held against beryllium at 1.2, carbon at 2.0 and
silicon at 5.0. `material_from_geometry.py` prints the range over every band it
emits and flags anything outside [1.1, 32].

`material_budget.py` is the check on the compression: it walks the same ray
through the shipped table and through a reduction of the geometry that keeps
every band, and the two agree to six percent on the ITk and twelve on the ODD.

## Still to do

- **Fit the spectrum over reference particles below 100 MeV**, which both
  loaders can produce (`min_pt_mev`) and which is currently thrown away. No
  third parameter needed, and it is the largest remaining defect.
- **A secondary momentum spread that grows with the parent**, as its median
  already does. One number cannot span the reference's 0.56 to 2.08, and that is
  the whole of the ITk's mean secondary momentum of 0.93.
- **Fit the material per ring against the reference** rather than only against
  the geometry. Only the overall normalisation is degenerate with the rates, so
  `N - 1` of `N` surfaces are measurable, and it is a division rather than a
  fit: the secondaries a surface produces divided by the primary crossings that
  made them, in both samples, with the flux cancelling. `implied_material.py`
  does this per (r, \|z\|) cell and would need attributing to surfaces instead.
  Splitting `X0` from `L0` needs the reference split by species, which the ITk
  dump supports through `Part_pdg_id`.
- **The ODD's decay channel is starved**: `decayYield` fits to 0.012 against the
  ITk's 0.108, and the \|d0\| > 100 mm tail is 0.022 of the secondary space
  points against the reference's 0.083. V0s at large radius are what fill that
  tail. `measure_secondary_populations.py` already reads ColliderML truth, so
  measure it instead.
- **Carry each layout's residual material error into its rate.** The closure
  test above says the ITk is 6 % light and the ODD 12 % heavy against their own
  geometries, which is the whole of the 24 % their fitted rates disagree by.
  That is a question of where the reduction still loses material, not of the
  model.
- **Cache the reference in `implied_material.py`**, which reloads the full
  sample on every run where the other scripts share `sample-*.npz`.
- **Re-measure the rest of `ablate.py`**, whose table predates the presets and
  the figures it scores. Its baseline arguments are also stale, saying one and
  two turns where the presets carry three.
- **Revisit the stub channel now that tracks range out.** `stubRate` was
  measured as what a full simulation has beyond the interaction-product law
  continued downwards. Part of that population the model now produces itself,
  the soft daughters stopping after a crossing or two, so the two may be double
  counting.
