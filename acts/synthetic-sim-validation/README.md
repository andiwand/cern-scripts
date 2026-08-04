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
    --fastsim /tmp/fastsim-itk --events 250 --skip-events 250 -o plots

# ODD, against ColliderML ttbar at a pile-up of 200; the shard is downloaded
# from HuggingFace on first use and cached
./validate.py odd --fastsim /tmp/fastsim-odd --events 50 --skip-events 50 -o plots
```

Plots land in `plots/<detector>/` as PDF so the two comparisons do not overwrite
each other; `--format png` for a raster. Everything is normalised per event, so
the samples are comparable whatever number of events each holds - but give
`dump_fastsim.py` as many events as the reference has, or the fast-simulation
line carries several times the noise of the line it is read against.
`fastsim.load` globs the prefix, so clear the old CSVs before a shorter run.

`dump_fastsim.py` generates from the shipped preset through the Python bindings;
`ActsBenchmarkSyntheticEventGeneration --layout itk-pixel --dump <prefix>` writes
the same two files faster, where the benchmark is built.

The two shipped presets came out of

```sh
./fit_event_config.py itk --fullsim '<dump>*.root' --events 250 \
    --path-length 4 --turns 3 --set secondaryKt=0.319 \
    --set stubRate=1.267 --set stubClusters=2.1 --set stubReach=4.0
./fit_event_config.py odd --events 50 --path-length 4 --turns 3 \
    --set secondaryKt=0.319 \
    --set stubRate=1.800 --set stubClusters=2.1 --set stubReach=4.0
```

which print `EventConfig::itkPixelTtbarPu200` and
`EventConfig::openDataDetectorTtbarPu200` as C++ to paste. The two halves are
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
| `sample.py` | the `Sample` every loader produces and `validate.py` plots |
| `fullsim_itk.py`, `fullsim_colliderml.py`, `fastsim.py` | one loader per sample format, so a third full simulation means one more file |
| `dump_fastsim.py` | generate an event from a preset and write the CSV pair |
| `validate.py` | the comparison and its plots |
| `scorecard.py` | the scored figures for a shipped preset, in a minute |
| `fit_event_config.py` | fit `EventConfig` to a reference, print it as C++ |
| `ablate.py` | remove one term of the model at a time and score what is left |
| `itk_layout_from_xml.py` | the ITk layout, out of the ATLAS GeoModelXml |
| `layout_from_geometry.py` | the ODD and Generic layouts, out of the ACTS geometry |
| `material_from_geometry.py` | the material half of the same, matched onto a shipped description |
| `material_budget.py` | what a ray collects in a shipped layout, against the geometry it was read from |
| `measure_secondary_kinematics.py` | the secondary momentum and kick laws, off the dump's parent links |
| `measure_secondary_populations.py` | the same on ColliderML, which has no truth-link threshold; also the stub channel |
| `measure_overlaps.py` | module overlap, off the dump's own module identifiers |
| `implied_material.py` | what material profile the reference asks for, cell by cell in (r, \|z\|) |
| `reference_scatter.py` | whether a mismatch is the model or the reference's own noise |

The first seven are the pipeline; the rest each answer a question the fit cannot,
and each produced a number that is now pinned in a preset rather than fitted.

### Layouts and material are read, not fitted

A geometry is a known thing and should not be fitted to simulated data. Each
shipped layout is read out of the authoritative description of its detector and
pasted into `Fatras/src/Synthetic/DetectorLayout.cpp`:

```sh
# the ITk, out of the official GeoModelXml. Needs a CERN account.
git clone ssh://git@gitlab.cern.ch:7999/Atlas-Inner-Tracking/ITKLayouts.git
python itk_layout_from_xml.py ITKLayouts            # --report for the sections

# the ODD and the Generic detector, out of the geometry ACTS builds for them
python layout_from_geometry.py odd
python layout_from_geometry.py generic --report

# the material of any of them, including the ITk's
python material_from_geometry.py itk

# and what the result collects along a ray, against the geometry it came from
python material_budget.py itk
```

`layout_from_geometry.py` is just `makeLayoutFromTrackingGeometry`, so for a
detector ACTS can build there is nothing to transcribe, and
`Python/Examples/tests/test_fatras_synthetic_layout.py` checks that the pasted
numbers still match the geometry. The ITk has no ACTS geometry to reduce
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

## Where it stands

`scorecard.py` on the half the fit never saw - 250 events for the ITk, 50 for the
ODD - averaged over five realisations. A mismatch wants to be zero, a ratio one.

| | shape | prod z | sec eta | prim eta | \|d0\| | sp | prim sp | decays | sec pt | sec hits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ITk | 0.075 | 0.096 | 0.032 | 0.002 | 0.023 | 0.99 | 0.97 | 0.94 | 1.01 | 0.97 |
| ODD | 0.018 | 0.422 | 0.010 | 0.002 | 0.431 | 0.99 | 1.02 | 0.92 | 1.24 | 1.09 |

Before the propagation defects below were fixed and the presets refitted, the
same two rows read 0.109 / 0.085 / 0.029 / 0.002 / 0.051 / 0.97 / 0.96 / 0.96 /
1.01 / 0.96 and 0.027 / 0.463 / 0.014 / 0.002 / 0.526 / 1.00 / 1.02 / 1.00 /
1.24 / 1.09. The spatial shape and \|d0\| carry the change; the ITk's `prod z`
and `sec eta` gave a little back, which is the fit trading them for a count that
now lands on one.

Know the noise before reading any of it: see the first item under "How the
objective has to be built". Roughly 0.01 on the ITk's \|d0\|, 0.03 on the ODD's,
0.005 on `prod z`, and `shape` reproduces to three decimals.

`validate.py` on the same halves, per event and normalised to the reference:

| | ITk | ODD |
| --- | --- | --- |
| space points | 0.99 | 0.99 |
| &nbsp;&nbsp;primary, inside the generated acceptance | 0.97 | 1.02 |
| &nbsp;&nbsp;primary, outside it | 1.03 | 1.16 |
| &nbsp;&nbsp;non-primary | 1.00 | 0.95 |
| primaries / event | 0.98 | 1.00 |
| mean primary hits | 0.99 | 1.02 |
| mean secondary pT | 1.02 | 1.22 |
| mean secondary hits | 0.97 | 1.10 |

The ITk column used to read a flat 0.94 on every row. Half of that was the
fifty-event split and half the propagation defects; the primary clusters
*outside* the acceptance were 1.04 and the ODD's 1.29, and ranging out is what
brought the ODD's to 1.16 - those are the sub-100-MeV curlers that used to run
on through the whole detector.

The truth-level secondary *count* is not quoted: the ITk dump lists only the
secondaries it kept truth for, some 5 400 per event against the 147 000
non-primary space points they cannot account for, so the ratio is a statement
about the dump's threshold rather than about the model. Compare the non-primary
space points.

Nothing about a surface is fitted. What the shipped presets carry:

- **Read off the geometry**: every surface position, every escape bound, and the
  material itself - a banded `MaterialSlab` per surface with X0 and L0
  independent, plus the passive service surfaces, all generated by
  `material_from_geometry.py`. No weight in sensors, no hardcoded silicon or
  carbon anywhere.
- **Measured on the reference, then pinned**: the module overlap probability and
  its offset, the secondary momentum and kick laws, the evaporation share and
  scale, the stub channel, the cluster resolution.
- **Fitted**: `chargedPerUnitRapidity`, `ptScale`/`ptExponent`, `d0Sigma`,
  `beamspotSigmaZ`, one secondary rate (the second follows it at a measured
  ratio), `decayYield` and `rapidityEdge`/`rapidityEdgeWidth`. Seven fewer than
  before: the endcap yield profile, its ring weights, the material weights and
  `secondaryRadialFraction` are all gone. The last fitted to zero on both
  detectors, having been 0.25 and 0.10 - it was standing in for material in the
  wrong place, and the electron channel being radial is the physics that
  remains.

Four known gaps, in order of size:

1. **The ODD's forward secondary production is still short** beyond
   \|z\| = 900, though banding the material took `prod z` from 1.7 to 0.49 and
   the 600-700 mm band from 0.32 to 0.91. What is left is 0.4 to 0.6 past a
   metre, which is where its geometry runs out of mapped material too.
2. **The ODD's V0 channel is starved.** `decayYield` fits to 0.015 against the
   ITk's 0.185, and its \|d0\| > 100 mm tail holds 0.025 of the secondary space
   points against the reference's 0.083. Scaling the decay length with the parent
   momentum closed that gap on the ITk - 0.066 against 0.070 - but there is
   almost nothing on the ODD to scale, so this is a yield to be measured on
   ColliderML truth rather than fitted.
3. **The ODD's mean secondary momentum is a fifth high** at 1.24, unmoved by
   anything tried. One spread cannot span the reference's 0.56 to 2.08; see
   "Still to do".
4. **The soft end of the spectrum runs high** below 100 MeV, the invariant
   Hagedorn form over-extrapolating below the range it was fitted in.

### What the fit is sensitive to

Each observable is driven by essentially one parameter, which is why the fit
converges at all. A configuration is per detector: running one detector's numbers
on another's layout is wrong by more than the generator's own coarseness.

| observable | parameter |
| --- | --- |
| space points / event | `secondaryRate` |
| primaries / event | `chargedPerUnitRapidity` |
| primary `dN/deta` shape | `rapidityEdge`, `rapidityEdgeWidth` |
| high-momentum tail | `ptExponent` |
| mean primary pT | `ptScale` |
| d0 core width | `d0Sigma` |
| z0 core width | `beamspotSigmaZ` |
| mean secondary pT | `secondaryMomentumScale`, `secondaryMomentumExponent` |
| secondaries born inside the beam pipe | `decayYield` |
| where the secondaries are produced, in \|z\| and r | the *material* of the layout, which is read and not fitted |
| the backward hemisphere and the central `dN/deta` | `secondaryEvaporationFraction` |

### How the objective has to be built

Four constraints, each of which was learned by getting it wrong first.

- **Bands, not bins.** A radial bin narrow enough to fall inside one layer
  measures the half-millimetre between a layout's layer radius and the
  reference's cluster positions, which no secondary model can move. On forty
  bins the objective sits at 0.132 to 0.135 for every variant tried, including
  ones differing by a factor two forward. `validate.ITK_BANDS` and `ODD_BANDS`
  are coarse enough that no band splits a layer.
- **The non-primary component alone, not the total.** `secondaryRate` is solved
  for the total, so a model that puts its secondaries in the wrong place scores
  exactly like one that does not. Every loader carries a per-space-point
  `sp_primary` flag for this.
- **Per particle, not only per cluster.** A secondary on the ITk's outermost
  disc leaves *one* space point, so fifteen times too many of them there barely
  moves a cluster profile. `Target.secondary_prod_z`, `secondary_hits` and
  `secondary_eta` close that.
- **A seed-averaged grid, not a simplex.** A Nelder-Mead run started at
  `(1500, 3.0)` never left the ridge it began on and scored well while being a
  factor four out, because the objective it was given - the non-primary *space
  point* profile - could not see the error at all.
- **Fifty events a half, not five.** The primary multiplicity of a ttbar pu200
  event swings 9 to 11 % event to event, so N events fix
  `chargedPerUnitRapidity` to about `10/sqrt(N)` percent: 4.6 % at five, 1.4 %
  at fifty. Both halves are spread over the ten dump files rather than taken
  from the front. This was worth more than any single modelling change. A
  six-event scan read against a fifty-event baseline is not a measurement at
  all: production-profile differences below about 0.3 are noise at that size.

- **Know the scorecard's own noise before reading it.** Removing
  `secondaryRadialFraction`, which was zero in both presets, is behaviour-neutral
  and changes only the random stream. It moved the ITk's `|d0|` from 0.012 to
  0.021 and the ODD's from 0.416 to 0.384. That is the floor: anything smaller
  than about 0.01 on the ITk's `|d0|` or 0.03 on the ODD's is a realisation and
  not a result. `shape` was identical to three decimals across the same change
  and is the most trustworthy figure of the set.

`chargedPerUnitRapidity` needs a note. The familiar minimum-bias 6.6 per unit of
pseudorapidity is the density at *central* eta, while the generator spreads it
flat over \|y\| < 4.3 where the real distribution falls off forward. Both
references give 5.1 to 5.3 averaged over that range. ColliderML's particle table
also contains charged *resonances* - rho+-, K*+-, Delta - which decay before any
sensor, so cutting on long-lived species is what makes its count agree with the
ITk dump's.

### The closure test: fitted material against aggregated material

The two secondary rates are *per radiation length* and *per nuclear interaction
length*. Nothing about them is a property of a detector, so the same numbers have
to come out of the ITk and out of the ODD - and if they do not, the difference is
the material each layout is carrying wrongly. It is the sharpest test there is on
the material, because it is the data speaking and not the geometry twice.

| | ITk | ODD | ITk / ODD |
| --- | --- | --- | --- |
| fitted `secondaryNuclearRate` | 7.483 | 6.410 | **1.167** |
| shipped / geometry `x/L0`, \|eta\| < 3 | 0.942 | 1.124 | 0.838 |

Only the nuclear rate is quoted, and deliberately. `solve_secondary_rate` scales
both rates by one factor - the ratio between them is measured from the electron
share of the daughters, not fitted - so `secondaryElectronRate` would give the
same 1.242 by construction and adding its row would dress one degree of freedom
up as two.

The product is **0.98**: correct each layout onto its own geometry and the two
detectors agree on secondaries per `L0` to two percent, across two full
simulations with two different definitions of what a secondary is. It was 1.04
before the propagation defects were fixed, so the residual disagreement is now
smaller than either layout's own material error.
`material_budget.py --closure-eta 3` prints the third row, and the bound matters
- past \|eta\| = 3.2 the ODD's map runs out of material while the shipped layout
still has some. Worth repeating whenever the reduction changes; it costs two fits
and is the only figure that separates a material error from a kinematics error.

## What was tried

Roughly chronological. Each of these was a real measurement or a real mistake;
the detail is in the git history of this file if it is ever wanted again. The
yield-profile entries are history: the profile implied about twice the ITk's real
radiation length and is gone.

**Getting the reference right**

- **The z0 of the primaries was never wrong.** It looked wrong for months. A
  pile-up event holds 204 distinct vertices and forty primaries share each one's
  z exactly, so a five-event histogram has the statistics of a thousand draws -
  15 to 30 % bin to bin. Against the reference's own scatter the model sits at
  chi2/ndf = 0.49. `reference_scatter.py` is that check for any field.
- **Barcodes are not unique within a GNN4ITk event**, only within one pile-up
  interaction. The key is `(Part_event_number, Part_barcode)`. Keying on the
  barcode alone inflated the mean hit count from 9.7 to 113.8.
- **Only generator particles carry a HepMC status** in that dump. Detector
  secondaries encode the Geant4 process instead (20001, 100001, ...), so
  applying `Part_status == 1` to everything removes every secondary. Primary
  versus secondary is `Part_barcode < 200000`.
- **ColliderML's `perigee_d0`/`perigee_z0` are NaN for a fifth of its charged
  particles** and its d0 sign convention is inverted, so both loaders compute
  impact parameters from the production vertex and the momentum instead. Its
  `primary` flag is narrower than Athena's: heavy-flavour decay products are
  secondaries there.
- **The truth-link threshold is in everything.** A full simulation records a
  secondary only above a few hundred MeV, and two thirds of the real ones fall
  below it. Every quantity read through that cut and then used as a property of
  the population was wrong, and three separate parameters were wrong that way.

**The layouts**

- **The ITk endcap is rings, not discs.** 75 discs per side carrying 95 rings,
  each one module deep - forty millimetres of radius out of three hundred - so a
  track crossing a disc usually crosses no silicon. Grouping the dump's clusters
  by `(barrel_endcap, layer_disk, eta_module)` resolves the same 95 rings, every
  position agreeing with the XML to half a millimetre. The barrel is genuinely
  *short*: beyond \|z\| = 374.6 mm the outer layers continue as inclined rings
  Athena labels endcap.
- **An ODD endcap layer is two rings staggered in z, not separated in r.** They
  overlap by five millimetres, which is the real detector's module overlap.
  Modelling the 4.2/2.8 mm stagger is all the ring structure buys there - the
  opposite of the ITk, where the radial gaps carry the physics.
- **Resolving rings needs a guard.** Two z planes covering the *same* radii are
  one ring alternating in z, and splitting them gives a track two space points
  where the detector gives it one. `maxRingOverlap` is the discriminator, and it
  has to be checked over every pair of planes: the Generic strip endcap
  interleaves its rings.
- **The reduction was placing every module at its envelope rather than at its
  centre.** A module is a plane tangent to its cylinder, so its centre is nearer
  the beam than any of its corners - and the fallback written for cylinders and
  discs, which have no radius at their centre at all, was firing on all of them.
  It put the ODD's innermost pixel layer at 33.27 mm where its sensors are at
  32.21, the sagitta of the chord and so worst at the smallest radius.
- **The generic detector was building two coincident discs at every endcap `z`**,
  a literal table and a leftover loop both filling `description.discs`. Every
  endcap crossing there gave two space points and twice the material.
- **Material is matched to surfaces in build order, not by coordinate.**
  `makeLayout` compared reference coordinates with `==`, so two surfaces at the
  same one - which is what an endcap layer split into rings staggered in z is -
  both took whichever description came last. It bit twice before, in the
  reduction and in the generic detector's coincident discs; the layout builder
  now records what each surface carries as it adds it.
- **The ODD layout is exact to a millimetre**, checked cluster by cluster against
  ColliderML, including the 1.8 mm offset between a barrel module's envelope and
  its silicon. **Rings cost 12 % of generation time** and nothing else, so there
  is no reason to offer the coarse layout as an option.

**The material**

- **A secondary counts in two lengths, not one.** Only knocked-out electrons
  follow X0; an interaction product follows L0, and the two run apart with
  composition - `L0/X0` is 4.96 for silicon, 2.01 for carbon fibre, 1.19 for
  beryllium, 10.67 for copper. Supports and services are low-Z, so per radiation
  length they interact two to four times as often as the silicon the rate was
  calibrated on. The electron fraction stops being free and becomes a property
  of the surface.
- **`yieldWeight` is gone, and four bugs were under it.** Turning
  `includeMaterialSurfaces` on needed all four: a surface's radius came from
  `perp(centre)`, so every mapped layer surface reduced to r = 0 and the switch
  had never worked; every material surface in a `(volume, layer)` group was
  summed, which double-counts the ITk's six coincident cylinders at r = 124;
  `materialOf` sampled a 50x50 binned map along one axis with the other pinned
  at zero; and passive surfaces were built unbounded although the reduction knew
  their extent. ITk `x/X0` at \|eta\| = 3 went **7.4 -> 6.0 -> 1.50 -> 1.32** as
  those landed, against roughly 1.2 to 1.6 for the whole real ITk.
- **L0 was not what the yield profile was standing in for.** Measured per
  surface, the nuclear gain over silicon is 1.14 at the innermost ITk disc and
  1.22 at the outermost - flat in z, against the profile's 1.5 to 6.7. Even at
  beryllium the total yield gain caps at 2.0x against the 5x the forward region
  wanted. Correcting the composition is right and does not close the gap.
- **Do not close the remaining gap with more material.** A fitted endcap profile
  `1 + (|z|/1800)^2` scores better than anything else tried and implies 1.9 X0
  at \|eta\| = 3 for the *pixels alone*, against roughly 1.2-1.3 for the
  **whole** ITk (arXiv 2412.15090, fig. 5). It is not real material.
- **A surface's average is not its material, and five bugs were under that.**
  Read against the maps at their own resolution the one-slab ITk was **1.65
  times too heavy at `eta = 0`** - three service cylinders run its whole length
  at 0.012 `x/X0` centrally and 0.074 at the far end, and averaged whole they
  hand the barrel the endcap's services - and the ODD a quarter too light in
  `x/L0` beyond `eta = 2.5`. Banding took the ITk ratio to 1.00 at `eta = 0`.
- The four that banding exposed: the ITk's shipped **beam pipe was the pixel
  volume boundary** at r = 25.3 rather than the real wall at 23.9 with four
  times the material; the **ODD's beam pipe was diluted by its own length**,
  0.164 mm of beryllium averaged over `|z| < 4000` where it only reaches 800,
  where banded it is the textbook 0.82 mm; the reduction **called the ITk's
  innermost endcap rings cylinders**, 20 mm wide in `r` and thin enough to pass
  the barrel test on their own, leaving five discs per side with no material;
  and **material was matched to surfaces by reference coordinate**, so three
  rings of one ITk disc at the same `z` all took whichever came last. It is
  matched in build order now.
- **Mapped material is accumulated, not a substance.** Its `Ar`, `Z` and molar
  density are whatever reproduces the lengths, so a fitted `L0/X0` is *not*
  bounded by the 1.19 to 10.7 of real materials, and the molar density of the
  ITk's "silicon" reads a thousand times below the physical value.
- **All three beam pipes were vacuum for a while.** `beamPipeMaterialWeight`
  went with the other weights, and the generator only searched the *pixel*
  volumes, where a beam pipe is not. It cost the ODD a factor two on its
  secondary \|eta\|.
- **Banding the composition, not only the amount**, took the ITk's `x/L0`
  closure from 0.912 to 0.942 where its `x/X0` sits at 0.941: the two lengths
  now agree on how far the layout is from its geometry, which is what they
  should do if the only thing left is compression. Merging neighbours whose
  *both* lengths agree to 20 % leaves the ITk at 743 bands over 161 surfaces.
- **Multiple scattering and energy loss displace the hit, not the helix.** Both
  are linearisations accumulated as running sums along the track. That is what
  gives a seed its impact parameter and curvature spread.
- **A track that cannot pay for the next surface stops there.** Energy loss now
  runs to the end rather than being capped, and a crossing costing more than the
  kinetic energy left ends the track after the cluster it made. That is ranging
  out, off the material the layout already carries and with no parameter of its
  own, and it is what `maxTurns` and part of the stub channel were standing in
  for. Worth 0.093 to 0.069 on the ITk's spatial shape and 0.027 to 0.017 on the
  ODD's, the largest single move since the material was banded.
- **Highland's logarithm is a function of the whole path, not of the slab in
  front.** Read per crossing it sits at 0.74 for a pixel layer where the
  accumulated path asks for about 0.9, so the model under-scattered by a fifth
  on exactly the layers that matter.

**The secondary model**

- **A Rayleigh scale is not a Rayleigh median.** `secondaryKt` stood at 0.310,
  which was a measured *median* (`= 1.177 sigma`). Measured three ways and
  weighted onto the primary spectrum the generator actually has, the scale is
  0.267 +- 0.010. It has to be pinned rather than fitted: free and scored on
  \|d0\| it runs to the top of any grid, buying the far end of \|d0\| with a
  secondary momentum the objective cannot see.
- **The momentum law was measured through the truth-link threshold** and was a
  factor two out. The cut removes half the daughters at *every* parent momentum,
  so there is no region where it can be ignored. Two truncation-aware estimators
  agree, and ColliderML - which has parent links and no threshold - measures the
  same law directly.
- **The kick is drawn beside the momentum, not out of it.** The dump's parent
  links say the two are independent: the Rayleigh scale of the kick is flat at
  0.3 GeV across every band of longitudinal momentum. Deriving the angle from
  the whole momentum forces a hard daughter to be collinear, which no tuning
  fixes, and tilted the secondary `dN/deta` by a factor two - re-emitting the
  *reference's own* secondaries with the old kernel reproduces the tilt, which
  is what pins it on the kernel rather than on the material.
- **The opening angle had a delta at exactly 90 degrees.** `sin = min(kT/p, 1)`
  folds the backward hemisphere onto the forward one and clamps every draw it
  cannot pay for onto a right angle: a tenth of the daughters above 100 MeV, and
  a right-angle daughter of a forward parent is central. Drawing the direction
  from the Fisher distribution at concentration `(p/kT)^2` carries both limits
  on the parameter that was already there, and the ODD's secondary `dN/deta`
  spread went 0.24 to 0.16.
- **Three channels, split by `Part_pdg_id`.** Electrons are 14 % of daughters
  above 300 MeV at `sqrt(<kT^2>/2)` = 0.014 and median p 2.67; hadrons are the
  rest at 0.299 and 0.70. The electrons that survive a truth-link threshold are
  *conversion pairs*, not delta rays - median `cos(theta)` is 1.000 to three
  decimals. They matter far beyond their 14 %: a channel's kick is a *floor*
  under what its daughters carry, so giving every secondary the nuclear kick
  would empty the soft end and the stub channel.
- **The backward hemisphere is a channel of its own.** 12.7 % of the dump's
  secondaries go backward, a quarter below 600 MeV and essentially none above
  two GeV - the quasi-isotropic evaporation product, the `grey tracks` of
  nuclear emulsion. A kick about the parent cannot make one at any scale.
- **Every inward-going secondary was propagated as its mirror image.**
  `makeHelixFromPoint` took `minGamma` from `helixGammaAtRadius`, which is always
  the *outgoing* crossing of the production radius; a daughter emitted back
  towards the beam axis is on the inbound leg at `2 pi - gamma`. The circle was
  right and the particle was started at the wrong point on it, so it travelled
  outwards where it should have gone in, at the wrong azimuth, with `z0`
  displaced by `cotTheta * radius * (2 pi - 2 gamma)` - of order 100 mm for a
  soft daughter. It hit 13 % of propagated secondaries at `eta` 0.3, 24 % at 1.5
  and 34 % at 3.0, worst forward. `RebuildFromPoint` never caught it because it
  took its test point *from* `helixGammaAtRadius`, so the direction it derived
  was outbound by construction.
- **A V0's flight length scales with its momentum.** `decayLength` was
  documented as the K0S length at a GeV and then used flat, so a 5 GeV parent
  decayed where a soft one did and the far end of the secondary `|d0|` could not
  fill: `P(r > 300 mm)` was 0.7 %. Scaling it costs no parameter and took the
  ITk's `|d0|` mismatch from 0.039 to 0.018.
- **Half the secondaries have a neutral parent.** 49.5 % of secondary space
  points come from a daughter of a converted photon or a neutral hadron, born at
  r = 0, which does not bend and leaves nothing on the way. Those daughters are
  *radial* and their \|d0\| is their own curvature alone: the measured median
  matches `r^2/2R` band by band with no free parameter. That took the \|d0\|
  mismatch down by a factor five. It now fits to zero on both detectors, having
  been standing in for material in the wrong place.
- **There is no conversion component.** A `secondaryCollinearFraction` was set
  to the share of daughters born with kT below 10 MeV, which is the wrong
  quantity for a model with no photons: a collinear daughter here follows the
  *charged* parent, whose bend cancels the daughter's at equal charge, dumping
  everything into the innermost \|d0\| decade. Zero fits as well as the 0.02 it
  refitted to. The radial component is what it should have been.
- **Two thirds of a real secondary population is below 100 MeV**, leaving about
  two clusters each essentially where they were made. That is the stub channel,
  measured on ColliderML; it needs a rate of its own because a nucleus breaking
  up and a soft photon converting do not follow the interaction-product law.
- **`sec eta` was never a material problem.** The corrected momentum law
  recovered it; every \|z\| profile that recovered it instead cost the objective
  a factor five.
- **The ODD's hard secondaries are not a per-detector kick.** Fitted
  independently against ColliderML it lands on the ITk's fitted *and* measured
  value. What is left is the shape of the model's spectrum above the 100 MeV
  cut, not a scale.
- **`validate.py` was never showing hitless secondaries.** A fifth of the
  model's are, but `fastsim.load` cuts `numHits > 0` exactly as the two
  reference loaders do. Read the CSVs directly and the population is a different
  one - which is how they got blamed for the eta spike that was really the
  opening angle.

**The primaries**

- **The spectrum was missing its Jacobian.** The Hagedorn spectrum is the
  *invariant* one, `dN/dpT ~ pT (1 + pT/s)^-n`. Without the leading `pT` the fit
  is 6.6x worse inside its own range and 3.7x over below it, faking a turnover
  it cannot produce. Fixing it is what made a lower `minPt` possible at all.
- **The plateau is flat in rapidity, not in pseudorapidity.** The reference's
  primary `dN/deta` dips 9 % at eta = 0, the opposite of the textbook
  midrapidity peak, and it is the Jacobian: `dN/deta = (p/E) dN/dy`, and with a
  100 MeV threshold below the pion mass the soft end loses a third of its
  density centrally and none by \|eta\| = 2. Drawing the rapidity flat costs one
  factor and no new parameter, and took the eta shape from 9.7 % to 2.9 %.
- **The plateau has an edge, and it is worth two parameters.** Both references
  are flat in `dN/dy` to a third of a percent inside \|y\| = 2.4 and have lost a
  seventh of that by \|y\| = 3.3. Fitted against the primary `dN/deta` shape
  rather than read off the reference's own `dN/dy`, whose forward end is cut by
  \|eta\| < 4. Drawn by rejection against the flat plateau, so the primary count
  is untouched.
- **The primary column has an acceptance in it.** A twelfth of the ITk's primary
  clusters and a twentieth of the ODD's come from particles the generator is
  configured never to produce - below 100 MeV or beyond \|eta\| = 4 - so
  `secondaryRate` had been standing in for them. `validate.py` splits the two
  rows now. Those clusters are curlers, and standing in for them with
  secondaries is wrong in shape: a sub-100-MeV primary leaves 10.2 clusters over
  only 3.3 distinct layers, 78 % of them inside r = 130 mm. Generating them
  instead (`minPt` 0.02, `maxTurns` 3) leaves the ITk total unmoved but shifts
  12000 clusters an event into the column they belonged in.
- **A stiff track was crossing the barrel twice.** The helix meets every barrel
  radius again on the way back in and nothing rejected it. `escapeRadius`/
  `escapeHalfZ` are the *enclosing* tracker, not these pixel-only layouts: a
  300 MeV track arcs out to a metre through the strips and curls back.
- **Module overlap, measured off the dump's own module identifiers** rather than
  a distance cut, so a second cluster on a layer is an overlap when it is on a
  neighbouring module and a re-crossing otherwise. The rate is flat - one number
  per detector - and the pair is staggered along the surface *normal*, not
  around in phi. A model that only duplicates a hit produces something a seeder
  deduplicates. This took hits per primary from 0.89 to 1.01 (ITk) and 0.86 to
  1.05 (ODD) for 4 % of the CPU.
- **A layer is not only its modules.** The ODD's four
  `<support name="SupportCylinder">` entries at r = 37-39, 75-77, 120-122 and
  176-178 mm are where the reference's production radius peaks, and the first
  alone carries a fifth of its barrel secondaries. They are *not* in the ACTS
  ODD tracking geometry - the reduction keeps material for layers, and a shell
  between two layers belongs to neither - so they are transcribed from
  `OpenDataPixels.xml`. Adding them took the ODD's non-primary shape from 0.022
  to 0.013.
- **One path-length bound cannot serve a disc and a cylinder.** A cylinder is
  crossed `cosh(eta)` times less often per unit z and traversed `cosh(eta)`
  times more deeply, so its material per unit z cancels to a constant - which is
  what both references show along their beam pipes, flat to a metre. Bounding it
  at a module's aspect ratio breaks the cancellation above `|z| = bound * r`.
  Splitting the bound took the ODD's production `z` mismatch from 0.107 to 0.041
  and put the ITk's wall share at 18.5 %.

**On seeding**

- The seed counts fell by about a fifth after the endcap refit and the
  efficiencies did not move - fewer soft one-hit tracks scattered through the
  forward region making candidate pairs that go nowhere.
- **Efficiency does not discriminate** on this event: a forward primary leaves
  fourteen space points, so finding one true seed among them is easy for
  anything. Compare times and candidate pair counts. A seed counts as true when
  *three* of its space points come from one primary, which matters for GBTS,
  whose seeds are four to eleven long.
- **A GBTS connection table belongs to a layout**: its reach along z has to
  cover the ring sets of a resolved endcap, whose consecutive discs are not at
  consecutive radii. What GBTS still loses is the table rather than the cuts -
  its remaining 5 % sits at \|eta\| 1 to 1.5 where a hand-written table is
  weakest, and the ATLAS one is trained.

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
