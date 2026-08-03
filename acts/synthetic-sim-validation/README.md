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
    --fastsim /tmp/fastsim-itk --events 50 --skip-events 50 -o plots

# ODD, against ColliderML ttbar at a pile-up of 200; the shard is downloaded
# from HuggingFace on first use and cached
./validate.py odd --fastsim /tmp/fastsim-odd --events 50 --skip-events 50 -o plots
```

Plots land in `plots/<detector>/` as PDF so the two comparisons do not overwrite
each other; `--format png` for a raster. Everything is normalised per event, so
the samples are comparable whatever number of events each holds - but give
`dump_fastsim.py` as many events as the reference has, or the fast-simulation
line carries several times the noise of the line it is being read against.
`fastsim.load` globs the prefix, so clear the old CSVs before a shorter run.

`dump_fastsim.py` generates from the shipped preset through the Python bindings;
`ActsBenchmarkSyntheticEventGeneration --layout itk-pixel --dump <prefix>` writes
the same two files faster, where the benchmark is built.

The two shipped presets came out of

```sh
./fit_event_config.py itk --fullsim '<dump>*.root' --events 50 \
    --path-length 4 --turns 3 --fit-kick --set secondaryKt=0.25 \
    --set stubRate=1.267 --set stubClusters=2.1 --set stubReach=4.0
./fit_event_config.py odd --events 50 --path-length 4 --turns 3 \
    --fit-kick --set secondaryKt=0.25 \
    --set stubRate=1.800 --set stubClusters=2.1 --set stubReach=4.0
```

which print `EventConfig::itkPixelTtbarPu200` and
`EventConfig::openDataDetectorTtbarPu200` as C++ to paste. Fifty events either
side, the same number the validation gets, and the two halves disjoint:
`--events 50` takes the front of each ITk file and of the ODD shard,
`--events 50 --skip-events 50` in `validate.py` takes what follows. The stub
channel and the kick are passed in because they are measured elsewhere and this
fit does not touch them; left out they would silently go to zero and to the
fit's own answer.

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
| `fit_event_config.py` | fit `EventConfig` to a reference, print it as C++ |
| `ablate.py` | remove one term of the model at a time and score what is left |
| `itk_layout_from_xml.py` | the ITk layout, out of the ATLAS GeoModelXml |
| `layout_from_geometry.py` | the ODD and Generic layouts, out of the ACTS geometry |
| `material_from_geometry.py` | the material half of the same, matched onto a shipped description |
| `measure_secondary_kinematics.py` | the secondary momentum and kick laws, off the dump's parent links |
| `measure_secondary_populations.py` | the same on ColliderML, which has no truth-link threshold; also the stub channel |
| `measure_overlaps.py` | module overlap, off the dump's own module identifiers |
| `implied_material.py` | what material profile the reference asks for, cell by cell in (r, \|z\|) |
| `reference_scatter.py` | whether a mismatch is the model or the reference's own noise |

The first six are the pipeline; the rest each answer a question the fit cannot,
and each produced a number that is now pinned in a preset rather than fitted.

### Layouts are read, not fitted

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
```

`layout_from_geometry.py` is just `makeLayoutFromTrackingGeometry`, so for a
detector ACTS can build there is nothing to transcribe, and
`Python/Examples/tests/test_fatras_synthetic_layout.py` checks that the pasted
numbers still match the geometry. The ITk has no ACTS geometry to reduce
wholesale, hence the XML for its positions and `material_from_geometry.py` -
which builds `acts.examples.itk` - for its material. Run these with
`python <script>`, not the shebang: the shebang picks up a different interpreter
and DD4hep then fails to find its plugins.

## Where it stands

Fitted on one half of a reference sample and read on the other, fifty events
each, per event and normalised to the reference:

| | ITk | ODD |
| --- | --- | --- |
| space points | 0.95 | 1.01 |
| &nbsp;&nbsp;primary, inside the generated acceptance | 0.97 | 1.03 |
| &nbsp;&nbsp;primary, outside it | 1.16 | 1.31 |
| &nbsp;&nbsp;non-primary | 0.92 | 0.95 |
| primaries / event | 1.01 | 1.00 |
| mean secondary pT | 0.93 | 1.05 |
| mean secondary hits | 0.96 | 0.97 |
| primary `dN/deta` spread over \|eta\| < 2 | 2.9 % | 3.5 % |

Both beam-spot widths, the primary spectrum and the secondary production point
sit within a few percent by construction, being what the fit is scored on. What
the shipped presets carry, and where each number comes from:

- **Read off the geometry**: every surface position, every material weight, the
  escape bounds.
- **Measured on the reference, then pinned**: the module overlap probability and
  its offset, the secondary momentum and kick laws, the stub channel, the
  cluster resolution.
- **Fitted**: `chargedPerUnitRapidity`, `ptScale`/`ptExponent`, `d0Sigma`,
  `beamspotSigmaZ`, `secondaryRate`, `decayYield`, `secondaryRadialFraction`,
  and the two parameters of the endcap yield profile.

Three known gaps, in order of size:

1. **The soft end of the spectrum runs 1.74x high** below 100 MeV, the invariant
   Hagedorn form over-extrapolating below the range it was fitted in.
2. **Hits per primary are short in the barrel**, because no layout resolves the
   overlap of modules along z. The secondaries take up the slack.
3. **The rapidity plateau is flat where the real one falls away**, so beyond
   \|eta\| = 2.5 the model runs 4-8 % high.

### What the fit is sensitive to

Each observable is driven by essentially one parameter, which is why the fit
converges at all. A configuration is per detector: running one detector's numbers
on another's layout is wrong by more than the generator's own coarseness.

| observable | parameter |
| --- | --- |
| space points / event | `secondaryRate` |
| primaries / event | `chargedPerUnitRapidity` |
| high-momentum tail | `ptExponent` |
| mean primary pT | `ptScale` |
| d0 core width | `d0Sigma` |
| z0 core width | `beamspotSigmaZ` |
| mean secondary pT | `secondaryMomentumScale`, `secondaryMomentumExponent` |
| secondaries born inside the beam pipe | `decayYield` |
| where the secondaries are produced, in \|z\| | the endcap yield profile of the *layout* |
| the same, in r | the *ring* weights of the layout, `applyRingYieldWeights` |
| secondary \|d0\| in its innermost decades | `secondaryRadialFraction` |
| secondary \|d0\| in its outermost, and \|eta\| | `secondaryKt`, against the longitudinal momentum |

### How the objective has to be built

Four constraints, each of which was learned by getting it wrong first.

- **Bands, not bins.** A radial bin narrow enough to fall inside one layer
  measures the half-millimetre between a layout's layer radius and the
  reference's cluster positions, which no secondary model can move. On forty
  bins the objective sits at 0.132 to 0.135 for every variant tried, including
  ones differing by a factor two forward. `validate.ITK_BANDS` and
  `ODD_BANDS` are coarse enough that no band splits a layer.
- **The non-primary component alone, not the total.** `secondaryRate` is solved
  for the total, so a model that puts its secondaries in the wrong place scores
  exactly like one that does not. Every loader carries a per-space-point
  `sp_primary` flag for this.
- **Per particle, not only per cluster.** A secondary on the ITk's outermost
  disc leaves *one* space point, so fifteen times too many of them there barely
  moves a cluster profile. `Target.secondary_prod_z`, `secondary_hits` and
  `secondary_eta` close that, and are why the endcap profile stopped being a
  factor four out.
- **Fifty events a half, not five.** The primary multiplicity of a ttbar pu200
  event swings 9 to 11 % event to event, so N events fix
  `chargedPerUnitRapidity` to about `10/sqrt(N)` percent: 4.6 % at five, 1.4 %
  at fifty. Both halves are spread over the ten dump files rather than taken
  from the front. This was worth more than any single modelling change.

`chargedPerUnitRapidity` needs a note. The familiar minimum-bias 6.6 per unit of
pseudorapidity is the density at *central* eta, while the generator spreads it
flat over \|y\| < 4.3 where the real distribution falls off forward. Both
references give 5.1 to 5.3 averaged over that range. ColliderML's particle table
also contains charged *resonances* - rho+-, K*+-, Delta - which decay before any
sensor, so cutting on long-lived species is what makes its count agree with the
ITk dump's.

## What was tried

Roughly chronological. Each of these was a real measurement or a real mistake;
the detail is in the git history of this file if it is ever wanted again.

**Getting the reference right**

- **The z0 of the primaries was never wrong.** It looked wrong for months. A
  pile-up event holds 204 distinct vertices and forty primaries share each one's
  z exactly, so a five-event histogram has the statistics of a thousand draws -
  15 to 30 % bin to bin. Against the reference's own scatter the model sits at
  chi2/ndf = 0.49. `reference_scatter.py` is that check for any field.
- **Barcodes are not unique within a GNN4ITk event**, only within one pile-up
  interaction. The key is `(Part_event_number, Part_barcode)`. Keying on the
  barcode alone merged particles across interactions and inflated the mean hit
  count from 9.7 to 113.8.
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
- **The ODD layout is exact to a millimetre**, checked cluster by cluster
  against ColliderML, including the 1.8 mm offset between a barrel module's
  envelope and its silicon.
- **Rings cost 12 % of generation time** and nothing else, so there is no reason
  to offer the coarse layout as an option.

**The secondary model**

- **A Rayleigh scale is not a Rayleigh median.** `secondaryKt` stood at 0.310,
  which was a measured *median* (`= 1.177 sigma`). Measured three ways and
  weighted onto the primary spectrum the generator actually has, the scale is
  0.267 +- 0.010.
- **The momentum law was measured through the truth-link threshold** and was a
  factor two out. The cut removes half the daughters at *every* parent momentum,
  so there is no region where it can be ignored. Two truncation-aware estimators
  agree, and ColliderML - which has parent links and no threshold - measures the
  same law directly.
- **Half the secondaries have a neutral parent.** 49.5 % of secondary space
  points come from a daughter of a converted photon or a neutral hadron, born at
  r = 0, which does not bend and leaves nothing on the way. Those daughters are
  *radial*, and their \|d0\| is their own curvature alone: the measured median
  matches `r^2/2R` band by band with no free parameter.
  `secondaryRadialFraction` is that share and it took the \|d0\| mismatch down
  by a factor five, having been the worst figure on both detectors and immovable
  by every other parameter.
- **The kick has to be pinned once the radial component exists.** Free and
  scored on \|d0\| and \|eta\| it runs to the top of any grid, buying the far
  end of \|d0\| with a secondary momentum the objective cannot see.
- **There is no conversion component.** A `secondaryCollinearFraction` was set
  to the share of daughters born with kT below 10 MeV, which is the wrong
  quantity for a model with no photons: a collinear daughter here follows the
  *charged* parent, whose bend cancels the daughter's at equal charge, dumping
  everything into the innermost \|d0\| decade. Zero fits as well as the 0.02 it
  refitted to, so it was removed. The radial component is what it should have
  been.
- **The ODD's hard secondaries are not a per-detector kick.** Fitted
  independently against ColliderML it lands on 0.267 - the ITk's fitted *and*
  measured value. What is left is the shape of the model's spectrum above the
  100 MeV cut, not a scale.
- **Two thirds of a real secondary population is below 100 MeV**, leaving about
  two clusters each essentially where they were made. That is the stub channel,
  measured on ColliderML; it needs a rate of its own because a nucleus breaking
  up and a soft photon converting do not follow the interaction-product law.
- **`sec eta` was never a material problem.** The corrected momentum law
  recovered it; every \|z\| profile that recovered it instead cost the objective
  a factor five.

**The material**

- **The endcap profile was a factor four out and scored well.** A Nelder-Mead
  simplex started at `(1500, 3.0)` never left the ridge it began on, and the
  objective - the non-primary *space point* profile - could not see the error
  anyway. It gave the outermost ITk disc a weight of 49.6 where the reference
  asks for about ten. A seed-averaged grid plus a secondary-*production*
  objective fixed both halves.
- **A disc's material is spread across it, not just along z.** The outermost ITk
  ring set asks for about 2.5 times the innermost at every \|z\|, and it is not
  monotonic, so no power of r stands in for it. `RingBounds` and `DetectorLayer`
  carry a weight of their own now, filled from radial bands.
- **The ITk and the ODD are opposite.** The ITk's residual material is
  endcap-radial and its barrel weights are worth nothing once the rings are
  free; the ODD asks for no radial term at all and wants *barrel* weights
  instead.
- **The endcap "material" profile is really a missing-cluster correction**,
  which is why it is a `yieldWeight` and not a material: the ITk's material
  grows by three from the innermost disc to the outermost while the yield the
  reference asks for grows by twenty. Fitting one number to both would overstate
  the material five-fold and scatter every forward track five times too hard.
- **Material moved onto the geometry.** A surface carries an
  `Acts::MaterialSlab` rather than a weight, because the energy loss needs a
  composition and not only a thickness - a layer taken as carbon rather than
  silicon loses twice as much per radiation length.
- **Multiple scattering and energy loss displace the hit, not the helix.** Both
  are linearisations accumulated as running sums along the track: a scatter
  slides a hit by the angle times the lever arm, energy loss by half the
  curvature change times the lever arm squared. That is what gives a seed its
  impact parameter and curvature spread. `maxTurns` still has to be bounded by
  hand because the helix itself never loses energy.

**The primaries**

- **Module overlap, measured off the dump's own module identifiers** rather than
  a distance cut, so a second cluster on a layer is an overlap when it is on a
  neighbouring module and a re-crossing otherwise. The rate is flat - one number
  per detector - and the pair is staggered along the surface *normal*, not
  around in phi: adjacent staves alternate in radius and the overlap is that
  alternation seen edge on. A model that only duplicates a hit produces
  something a seeder deduplicates. This took hits per primary from 0.89 to 1.01
  (ITk) and 0.86 to 1.05 (ODD) for 4 % of the CPU.
- **The primary column has an acceptance in it.** A twelfth of the ITk's primary
  clusters and a twentieth of the ODD's come from particles the generator is
  configured never to produce - below 100 MeV or beyond \|eta\| = 4 - so
  `secondaryRate` had been standing in for them. `validate.py` splits the two
  rows now.
- **Those clusters are curlers, and standing in for them with secondaries is
  wrong in shape.** A sub-100-MeV primary leaves 10.2 clusters over only 3.3
  distinct layers, 78 % of them inside r = 130 mm, where a secondary would put
  them several layers further out.
- **The spectrum was missing its Jacobian.** The Hagedorn spectrum is the
  *invariant* one, `dN/dpT ~ pT (1 + pT/s)^-n`. Without the leading `pT` the fit
  is 6.6x worse inside its own range and 3.7x over below it, faking a turnover
  it cannot produce. Fixing it is what made a lower `minPt` possible at all.
- **A stiff track was crossing the barrel twice.** The helix meets every barrel
  radius again on the way back in and nothing rejected it - `maxTurns` bounds
  the turning angle and the layout had no outer edge. `escapeRadius`/
  `escapeHalfZ` are the *enclosing* tracker, not these pixel-only layouts: a
  300 MeV track arcs out to a metre through the strips and curls back.
- **Generating the soft primaries made the composition honest.** `minPt` 0.02,
  `maxTurns` 3: the ITk total does not move, but 12000 clusters an event shift
  out of the non-primary column into the primary one where they belonged, and
  `secondaryRate` falls with them.
- **The plateau is flat in rapidity, not in pseudorapidity.** The reference's
  primary `dN/deta` dips 9 % at eta = 0, which is the opposite of the textbook
  midrapidity peak and looks like a loader bug. It is the Jacobian:
  `dN/deta = (p/E) dN/dy`, and with a 100 MeV threshold below the pion mass the
  soft end loses a third of its density centrally and none by \|eta\| = 2.
  Sliced in pT the centre-to-shoulder ratio follows `p/E` exactly. Drawing the
  rapidity flat costs one factor and no new parameter, and took the eta shape
  from 9.7 % to 2.9 %.

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
- **Taper the rapidity plateau**, which is the forward half of the same
  overshoot.
- **A secondary momentum spread that grows with the parent**, as its median
  already does. One number cannot span the reference's 0.56 to 2.08, and that is
  the whole of the ITk's mean secondary momentum of 0.93.
- **A backward branch for the secondary momentum**: 11 % of the dump's daughters
  are emitted with negative longitudinal momentum and a log-normal cannot be.
- **Material on the beam pipe and along a barrel cylinder.** The ITk reference
  makes 8.8 % of its secondary hit weight in the beam pipe wall against the
  model's 0.4 %, and the ODD wants a barrel cylinder weighted differently at
  \|z\| < 250 than beyond it. `barrelModules` already splits a cylinder into eta
  modules, so a layer weight would reach the second.
- **Re-measure `ablate.py`**, whose table predates the presets, the figures it
  scores and the terms it can remove.
- **Split the ITk 250/250.** Its two fifty-event halves differ by a flat 5.2 %
  across every component, so its validation ratios read about that pessimistic.
  The dump has five hundred events; the ODD shard has a hundred and cannot.
