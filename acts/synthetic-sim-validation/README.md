# Validating the ACTS synthetic space point generator

`ActsFatras::Synthetic` is a deliberately coarse fast simulation that produces
space point events for seeding benchmarks. These scripts check that its
distributions are in the right place, which is the only claim it makes. Two of
its three shipped layouts have a full simulation to be checked against: the ITk
against a GNN4ITk Athena dump, the ODD against ColliderML.

## Running it

```sh
# one fast-simulation event per layout, written as two CSV files
python dump_fastsim.py itk -o /tmp/fastsim-itk
python dump_fastsim.py odd -o /tmp/fastsim-odd

# ITk, against a local GNN4ITk dump
./validate.py itk --fullsim ~/Downloads/user.avallier.*.DumpGNNITk_v9.root \
    --fastsim /tmp/fastsim-itk --events 5 -o plots

# ODD, against ColliderML ttbar at a pile-up of 200; the shard is downloaded
# from HuggingFace on first use and cached
./validate.py odd --fastsim /tmp/fastsim-odd --events 20 -o plots
```

Plots land in `plots/<detector>/` as PDF so the two comparisons do not overwrite
each other; `--format png` for a raster. Everything is normalised per event, so
the samples are comparable whatever number of events each holds.

`dump_fastsim.py` generates from the shipped preset through the Python bindings;
`ActsBenchmarkSyntheticEventGeneration --layout itk-pixel --dump <prefix>` writes
the same two files faster, where the benchmark is built.

`fit_event_config.py <detector>` fits `ActsFatras::Synthetic::EventConfig` to a
reference and prints it as the C++ of a preset, which is where
`EventConfig::itkPixelTtbarPu200` and `EventConfig::openDataDetectorTtbarPu200`
came from. The two shipped presets are

```sh
./fit_event_config.py itk --fullsim <dump>.root --events 5 \
    --path-length 4 --turns 1 --fit-kick
./fit_event_config.py odd --events 20 --path-length 4 --turns 2 \
    --endcap-material 784,2.99 --fit-kick
```

Three scripts measure rather than fit, and each answers a question the fit cannot:

```sh
# the secondary kinematics, off the dump's own parent links
./measure_secondary_kinematics.py ~/Downloads/'*DumpGNNITk_v9.root' --events 5

# what material profile the reference asks for, cell by cell in (r, |z|)
./implied_material.py --fullsim ~/Downloads/'*DumpGNNITk_v9.root' \
    --fastsim /tmp/fastsim-itk --events 5

# whether a mismatch in a plot is the model or the reference's own noise
./reference_scatter.py --fullsim ~/Downloads/'*DumpGNNITk_v9.root' \
    --fastsim /tmp/fastsim-itk --field z0
```

### Layouts are read, not fitted

A geometry is a known thing and should not be fitted to simulated data. Each
shipped layout is read out of the authoritative description of its detector, by
one of two scripts that print the C++ to paste into
`Fatras/src/Synthetic/DetectorLayout.cpp`:

```sh
# the ITk, out of the official GeoModelXml. Needs a CERN account.
git clone ssh://git@gitlab.cern.ch:7999/Atlas-Inner-Tracking/ITKLayouts.git
python itk_layout_from_xml.py ITKLayouts            # --report for the sections

# the ODD and the Generic detector, out of the geometry ACTS builds for them
python layout_from_geometry.py odd
python layout_from_geometry.py generic --report
```

The second is just `makeLayoutFromTrackingGeometry`, so for a detector ACTS can
build there is nothing to transcribe, and
`Python/Examples/tests/test_fatras_synthetic_layout.py` checks that the pasted
numbers still match the geometry. The ITk has no ACTS description, hence the XML.
Run both with `python <script>`, not the shebang: the shebang picks up a different
interpreter and DD4hep then fails to find its plugins.

One loader per sample format - `fullsim_itk.py`, `fullsim_colliderml.py`,
`fastsim.py` - each producing the `sample.Sample` that `validate.py` plots, so a
third full simulation means one more file.

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

## What the fit is sensitive to

Each observable is driven by essentially one parameter, which is why the fit
converges at all. A configuration is per detector: running one detector's numbers
on another's layout is wrong by more than the generator's own coarseness.

| observable | parameter |
| --- | --- |
| space points / event | `secondaryRate` |
| primaries / event | `chargedPerUnitEta` |
| high-momentum tail | `ptExponent` |
| mean primary pT | `ptScale` |
| d0 core width | `d0Sigma` |
| z0 core width | `beamspotSigmaZ` |
| mean secondary pT | `secondaryMomentumScale`, `secondaryMomentumExponent` |
| secondaries born inside the beam pipe | `decayYield` |
| **where the secondaries are produced, in \|z\|** | the endcap material profile of the *layout* |
| shape of the non-primary space points in \|z\| | the same, weakly -- see below |
| secondary \|d0\| by decade **and \|eta\|** | `secondaryKt`, against the longitudinal momentum |

### The objective has to be banded, and split by component

**Bands, not bins.** A radial bin narrow enough to fall inside one layer measures
the half-millimetre between a layout's layer radius and the reference's cluster
positions, which no secondary model can move. The *primary* space points, which
have no secondary model at all, scatter from 0.5 to 1.8 bin to bin on forty bins,
and on forty bins the objective sits at 0.132 to 0.135 for every variant tried
here, including ones differing by a factor two in the forward region.
`validate.ITK_BANDS` and `validate.ODD_BANDS` are coarse enough that no band
splits a layer.

**The non-primary component alone, not the total.** `secondaryRate` is solved
for the total, so a model that puts its secondaries in the wrong place scores
exactly like one that does not. Every loader therefore carries `sp_primary`, a
per-space-point flag: for the ITk a cluster is primary when any linked barcode
is below the Athena limit, for ColliderML when its particle link carries the
`primary` flag, for the fast simulation it is a column of the dump. An earlier
scan without this reported the material scales as unconstrained and had them
removed; its numbers - 0.161 / 0.149 / 0.141 / 0.133 as the term was weakened -
are all inside the noise floor of the objective it used.

**Space points are not enough, even split by component.** A secondary made on the
ITk's outermost disc leaves *one* space point, so fifteen times too many of them
there moves the non-primary cluster profile by almost nothing, and until the
sweep of 2026-08-01 nothing else in the objective counted secondaries at all.
That is how the fitted endcap profile came to be a factor four out and score well
throughout (see the sweep, where that failure is described).

Two figures close it, both per particle rather than per cluster:
`Target.secondary_prod_z`, the shape in \|z\| of where the secondaries are
*produced*, which is where the material term acts; and `Target.secondary_hits`,
how many space points one leaves, which separates the reference's secondaries
from a swarm of stubs standing in for them. A third, `Target.secondary_eta`,
closes the same gap for the opening angle. All three are in `FIGURES`, so
`ablate.py` scores them too.

`chargedPerUnitEta` needs a note. The familiar minimum-bias 6.6 per unit of
pseudorapidity is the density at *central* eta, while the generator spreads it
flat over |eta| < 4 where the real distribution falls off forward. Both references
give 5.1 to 5.3 averaged over that range: an ITk dump has 8.5k and ColliderML 8.5k
long-lived charged primaries per event above 100 MeV inside |eta| < 4, against the
10.6k a flat 6.6 produces. ColliderML's particle table also contains charged
*resonances* - rho+-, K*+-, Delta - which decay before any sensor: 43 % of its
charged primaries above 2 GeV leave no pixel cluster at all, and cutting on
long-lived species is what makes the count agree with the ITk dump's.

## ITk, on ttbar at a pile-up of 200

Five events of `DumpGNNITk_v9` against one generated event, after tuning. The
last column is the shipped preset before the sweep of 2026-08-01, on the same
five reference events and averaged over five seeds.

| | full sim | fast sim | ratio | before the sweep |
| --- | --- | --- | --- | --- |
| pixel space points / event | 219648 | 220328 | 1.00 | 1.00 |
| &nbsp;&nbsp;primary | 87529 | 74064 | 0.85 | 0.82 |
| &nbsp;&nbsp;non-primary | 132119 | 146264 | 1.11 | 1.12 |
| primaries / event | 8191 | 8192 | 1.00 | 1.00 |
| secondaries / event | 4761 | 20902 | 4.4 | 6.0 |
| mean primary pT | 0.60 GeV | 0.60 GeV | 0.99 | 0.99 |
| mean pixel hits, primaries | 9.7 | 9.0 | 0.93 | 0.90 |
| **mean pixel hits, secondaries** | **4.2** | **3.7** | **0.88** | **0.74** |
| secondaries born inside the beam pipe | 8.6 % | 8.5 % | 0.99 | 1.00 |
| non-primary shape mismatch | | 0.035 | | 0.082 |
| **secondary production \|z\| mismatch** | | **0.086** | | **0.324** |
| secondary \|d0\| mismatch | | 0.201 | | 0.312 |
| secondary \|eta\| mismatch | | 0.088 | | 0.033 |

Everything moved the right way except the secondary pseudorapidity.

Good:

- **Total space points per event** and the profile in r and |z| with it; **eta**,
  flat within the 13 % the reference itself is flat to; **phi**, flat in both,
  and the space point azimuth with it.
- **pT spectrum of the primaries**, now across the whole range: the tail reaches
  30 GeV as the reference does.
- **z0** and **d0**, both Gaussians of the fitted width. The reference's d0 has a
  tail past 0.05 mm that the fast simulation does not; those are decay products
  the generator makes as secondaries instead.
- **Hits per particle against eta**, now in magnitude and not only in shape. Both
  rise from 5 to 6 in the barrel to a peak near |eta| = 3 of 14 to 15, agreeing to
  within a few percent forward of |eta| = 1.5, which is what describing the endcap
  ring by ring buys.
- **Where the secondaries are made**, now within a third in every band of |z|
  against a factor two before, and the number of space points each leaves, 3.7
  against 4.2. Both come from the refitted endcap material profile.

Not so good:

- **The secondaries are 10 % too forward**, 0.088 folded into eight bands of
  |eta| against 0.033 before, the one figure that went backwards. It is the cost
  of a narrower opening angle: with the kick at the measured value a daughter
  follows its parent more closely, and the parents are forward-weighted because a
  forward primary crosses fourteen surfaces where a central one crosses five.
  Widening the kick back to the old 0.310 recovers it and costs a quarter of the
  |d0| agreement; the fit, scored on both, lands on the measured value. The *space
  points* are unaffected - their profile in r and |z| is better by a factor two.
- **Hits per particle are 7% low, and now only in the barrel.** The central
  plateau is 5.4 against 5.8; forward of |eta| = 1.5 the two agree. The residual
  is module overlap and nothing else, measured on the ODD shard below.
- **The primary/secondary split is wrong even though the total is right.** Four
  times too many secondaries, each with fewer hits, is what lands the total in the
  right place. Part of it is bookkeeping rather than physics: only about half the
  real pixel clusters carry a truth link at all, while every synthetic space point
  belongs to a particle, so the real "unlinked" component has no counterpart and
  the surplus secondaries stand in for it. That is what `secondaryRate` is
  documented to absorb, and tuning it to the space point count makes the surplus
  larger, not smaller. The two cannot both be matched, and the space point density
  is what a seeder sees.

### The ITk endcap is rings

The endcap is 75 disks per side carrying 95 rings, each ring one module deep —
forty millimetres of radius out of the three hundred the detector covers. So a
track crossing a disk usually crosses no silicon, which an envelope around the
rings cannot express, and the `z` distribution shows the difference directly. The
nine sections, from `ITKLayouts/data/Pixel/*Defines.gmx`:

| section | r [mm] | \|z\| [mm] | rings |
| --- | --- | --- | --- |
| InnerBarrel L0, L1 | 34, 99 | to 244, 245 | cylinders |
| OuterBarrel L2-L4 | 160, 228, 291 | to 374.6 | cylinders |
| InnerEndcap L0 | 42.8 | 263-1142 | 15 |
| InnerEndcap E0 | 68.3 | 1103-1846 | 6 |
| InnerEndcap L1 | 100.1 | 263-2621 | 23 |
| OuterIncline L2-L4 | 168.5, 235.0, 297.4 | 397-1039 | 6, 8, 9 |
| OuterEndcap L2-L4 | 174.6, 234.7, 294.7 | 1146-2850 | 11, 8, 9 |

The barrel is *short*, and correctly so: the outer three layers are flat only to
|z| = 374.6 mm and the inner two to 244 mm, beyond which the layer continues as
inclined rings that Athena labels endcap. A barrel that looks too short next to
the detector's overall length is the geometry, not a mistake.

The reading is checkable. Grouping the dump's clusters by (`CLbarrel_endcap`,
`CLlayer_disk`, `CLeta_module`) resolves the same 95 rings, every position
agreeing with the XML to better than half a millimetre and every radial extent to
better than one. Resolving `CLeta_module` is what makes the endcap intelligible:
grouped by layer alone, a layer looks like a ring at fixed radius spanning a metre
of z, which the model cannot express at all.

## ODD, against ColliderML ttbar at a pile-up of 200

`CERN/ColliderML-Release-1` on HuggingFace is the ODD's own full simulation -
Geant4 through Key4hep on the same geometry, digitised with ACTS geometric
channelisation at a 50 x 50 um pixel pitch - so a row of its `tracker_hits` table
is a cluster, which is what a space point generator produces. Twenty events of
`ttbar_pu200` against one generated event; only pixel volumes 16, 17 and 18 are
read.

| | full sim | fast sim | ratio | before the sweep |
| --- | --- | --- | --- | --- |
| pixel space points / event | 101954 | 102532 | 1.01 | 1.04 |
| &nbsp;&nbsp;primary | 56772 | 45795 | 0.81 | 0.80 |
| &nbsp;&nbsp;non-primary | 45182 | 56737 | 1.26 | 1.31 |
| primaries / event | 8413 | 8416 | 1.00 | 1.00 |
| secondaries / event | 3970 | 14858 | 3.7 | 3.7 |
| mean primary pT | 0.63 GeV | 0.63 GeV | 1.00 | 1.00 |
| mean pixel hits, primaries | 6.2 | 5.4 | 0.88 | 0.80 |
| mean pixel hits, secondaries | 4.1 | 3.4 | 0.82 | 0.81 |
| **mean secondary pT** | | | **1.40** | **1.42** |
| secondaries born inside the beam pipe | 2.3 % | 2.2 % | 0.98 | 1.12 |
| non-primary shape mismatch | | 0.079 | | 0.095 |
| secondary production \|z\| mismatch | | 0.130 | | 0.125 |
| secondary \|d0\| mismatch | | 0.260 | | 0.289 |
| **secondary \|eta\| mismatch** | | **0.019** | | **0.034** |

The hits ratio is where the ODD moved most, 0.80 to 0.88, and the sweep did not
set out to move it: with the endcap material profile no longer over-weighted the
yields are lower everywhere, and the primaries formerly buried under surplus
secondaries are the same primaries. At the 1.26 clusters per layer crossing
measured below, 1.26 x 5.4 = 6.8 against the reference's 6.2, so module overlap
now more than covers the residual.

The mean secondary momentum is the one thing here the sweep did **not** fix, still
1.4 times the reference's; see the end of the sweep for what is left of it.

### The layout is right to a millimetre

This is the one layout that can be checked against a full simulation of the same
detector, and it comes out exact. Measured on the shard against
`openDataDetectorPixelDescription()`:

| | ColliderML | preset |
| --- | --- | --- |
| barrel radii [mm] | 32.5, 68.4, 114.3, 170.3 | 32.2, 68.2, 114.2, 170.2 |
| barrel half length [mm] | 507.2 | 507.25 |
| disk \|z\| [mm] | 618.8, 718.8, 838.9, 978.8, 1118.9, 1318.7, 1518.8 | 620.4, 720.4, 840.4, 980.4, 1120.4, 1320.4, 1520.4 |
| disk r [mm] | 42.0 ... 173.7 | 42.85 ... 173.79 |

The radii are means over the clusters of a layer, so a few tenths of a millimetre
is as close as this can come. The r-z occupancy plot is the same picture twice,
and it confirms the 1.8 mm sensor offset the preset carries: the silicon is at
32.2 mm, not the 34 mm `OpenDataPixels.xml` declares.

#### An ODD endcap layer is two rings, staggered in z but not separated in r

`layout_from_geometry.py odd` resolves each of the seven endcap layers into two
disks rather than one: the ring at r = 42.85-110.95 mm sits 4.2 mm short of the
nominal layer z and the one at r = 105.52-173.79 mm 2.8 mm beyond it. Modelling
that stagger is all the ring structure buys here, and it shows in the occupancy
plot as a small jog at r ~ 107 that both simulations now have. There is no radial
gap to buy: the two rings overlap by five millimetres, the module overlap of the
real detector. That is the opposite of the ITk, where the gaps carry the physics.

The overlap is also what makes resolving rings safe in general. Two z planes
covering the *same* radii are one ring whose modules alternate in z, and splitting
them would give a track two space points where the detector gives it one; the ITk
pixel endcap staggers the halves of a ring by 6 mm, so this is not hypothetical.
`maxRingOverlap` is the discriminator, checked over every pair of planes rather
than neighbours in z — the Generic detector's strip endcap interleaves its rings,
so the two halves of one ring can have another ring between them.

### What agrees, and what does not

Good, beyond the layout:

- **Space points per event, primaries per event, both beam-spot widths and both
  momentum spectra**, all to about a percent, these being what was fitted.
- **phi** and **eta**, flat in both.
- **Hits per particle in the endcap.** Both peak at |eta| ~ 3, at 8.0 against 9.0.
  The ODD endcap really is planar disks, so unlike the ITk the forward region is
  described rather than stood in for.
- **The cluster resolution is measured rather than assumed.** The core of
  ColliderML's cluster-to-truth residual in the barrel at normal incidence is 8 um,
  better than the 14 um a 50 um pitch gives digitally because its clusters are
  charge-weighted. Its *RMS* is 120 to 230 um - merged clusters, not resolution,
  and taking it for the resolution would be wrong by an order of magnitude.

Not so good:

- **Barrel hits per particle are flat at exactly 4.0**, one crossing per cylinder,
  against 6.0 in the full simulation. No parameter reaches this. Two effects are
  behind it, both measured on the shard: module overlaps give **1.26 clusters per
  layer crossing** at every momentum, and soft tracks cross the same layers
  repeatedly - a primary at |eta| < 0.5 leaves 12.9 pixel clusters on average
  between 100 and 200 MeV, up to 44, against 4.7 above 1 GeV. The synthetic helix
  takes one intersection per surface and can produce neither, which is the spike
  at eta = 0 in the full simulation against a plateau in the fast one, and why the
  barrel holds 40 % of the fast simulation's space points against 52 % of the
  reference's. The fix is propagation - a duplication probability per crossing for
  the overlaps, more than one turn for the curlers - not configuration.
- **Only two thirds of the real clusters belong to the population being
  compared.** Every ColliderML cluster carries a particle link, unlike the ITk
  dump, but 33% come from particles outside the generator's acceptance - below
  100 MeV or beyond |eta| = 4. The surplus secondaries stand in for a real
  component here too, just an identifiable one.
- **The ODD wants far less endcap material than the ITk**, 1.49 to 8.29 across the
  endcap against the ITk's 1 to 19.55. The term lives on the layout as a weight
  per surface rather than in the configuration, and the ODD's is small because the
  detector is built to be simple and carries little service material.
- **The ODD is short of primary space points in the *barrel***: 81 % of the
  reference's against the ITk's 85 %, because its barrel is one flat cylinder per
  radius where the ITk's is a barrel plus inclined rings, and no layout here
  resolves a module overlap. Its `maxTurns` of 2 against the ITk's 1 does double
  duty - loopers and overlaps - so expect it to fall back if the layout ever gains
  overlapping modules. This is why the ODD's non-primary shape mismatch is 0.079
  against the ITk's 0.035.
- **d0 has a tail the generator does not.** 5.6 % of ColliderML's primaries have
  |d0| beyond 2 mm, produced at a median radius of 28 mm: strange and
  heavy-flavour decay products the dataset still labels primary. The generator
  makes those as secondaries, so `d0Sigma` is the width of the luminous region and
  nothing more; widening it to cover the tail would count them twice.

## The sweep of 2026-08-01

These belong together because they are the same kind of mistake repeated: a number
measured or fitted correctly against an objective that could not see what it was
for.

### A Rayleigh scale is not a Rayleigh median

`secondaryKt` stood at 0.310 GeV, and its comment recorded what had been measured:
"the reference's median kT runs from 0.26 GeV for a parent below one GeV to
0.37 GeV for one above ten". Both numbers are right. Neither is a Rayleigh scale,
which is what the field is:

    median = sigma * sqrt(2 ln 2) = 1.177 sigma
    mean   = sigma * sqrt(pi / 2) = 1.253 sigma

`measure_secondary_kinematics.py` reports the scale three ways - from the median,
from the mean, and as the maximum likelihood `sqrt(<kT^2>/2)` - and their
agreement is the check that the sample really is Rayleigh. Over 835k secondaries
with a resolvable parent, weighted onto the primary spectrum the generator
actually has, they give **0.271 / 0.253 / 0.277**, so 0.267 +- 0.010.

The weighting matters as much as the conversion: the scale grows with the parent,
0.22 below a GeV to 0.33 above ten, the dump's secondary sample is biased towards
hard parents because a hard parent more often makes a daughter above the 300 MeV
truth-link threshold, and the generator's yield per crossing does not depend on
the parent at all.

The longitudinal momentum was wrong in a plainer way: its law was
`0.555 * p^0.245` against a measured `0.510 * p^0.567` with a spread of 1.81, so
60 % too hard for a parent below a GeV and half as hard for one at twenty. The
soft end is most of the population.

| parent p | dump median pL | old law | new law |
| --- | --- | --- | --- |
| 0.59 GeV | 0.352 | 0.482 | 0.372 |
| 1.44 GeV | 0.729 | 0.607 | 0.632 |
| 3.16 GeV | 0.982 | 0.736 | 0.995 |
| 6.95 GeV | 1.325 | 0.892 | 1.593 |
| 21.4 GeV | 3.077 | 1.170 | 3.079 |

### The endcap material profile was a factor four out, and scored well

`applyEndcapMaterialProfile(801, 3.06)` gives the outermost ITk disc a weight of
**49.6** - one crossing standing for fifty sensors and yielding eight secondaries.
`implied_material.py` divides the reference's secondaries in a cell of (r, |z|) by
the crossings that made them and gets about ten.

Two things let it through, both now fixed:

- `fit_endcap_material` was a Nelder-Mead simplex started at `(1500, 3.0)`. The
  objective has a long valley and it never left the ridge it began on. It is a
  seed-averaged grid now, `MATERIAL_GRID`.
- The objective was the non-primary *space point* profile, which cannot see the
  error at all, for the reason given above. Scored on where the secondaries are
  produced, the old profile comes out at 0.324 against 0.086 for the new one, and
  on the objective it was actually fitted with at 0.41 against 0.11, so it was not
  even the minimum of its own figure of merit.

The ITk profile is `(250, 1.20)` now: 1.0 in the barrel, 2.06 at the first disc at
|z| = 263 mm, 19.55 at the last at 2850 mm. The step onto the barrel is real - an
endcap disc carries the services of everything inboard of it and a barrel stave
does not, and the reference's own yield per crossing has the step too. The valley
is flat, so which point in it a run picks matters little: over ten seeds the four
best ITk settings sit within 0.114 to 0.131 on the fitted objective. What matters
is that a grid finds the basin and a simplex from a steep start does not.

The ODD's `(784, 2.99)` came through the sweep unchanged: scored on the secondary
production profile it is already the minimum. An endcap that never asks for more
than a factor 8.29 has no room for the ITk's failure to happen in.

### `implied_material.py` also shows what the model cannot express

At a fixed |z| the outermost radial band consistently asks for about 2.5 times the
weight of the innermost, all the way out. `materialWeight` is a property of a
`DetectorSurface`, so every ring of one disc shares one number and `RingBounds`
has none of its own. That is where the residual endcap structure lives, and
closing it means a weight per ring, not a better two-parameter profile. The barrel
shows the same more weakly - r 260-330 at |z| < 250 asks for about 2.4 times
r 60-130 - and `BarrelEndcapDescription::barrelMaterialWeights` is empty for the
ITk.

### The z0 of the primaries was never wrong

It looked wrong for a long time in `primaries.pdf`, where the reference's core
stands well above the model's. It is the reference's own noise: a pile-up event
holds **204 distinct primary vertices** and some forty primaries share each vertex
z exactly, so a five-event reference histogram has the statistics of a thousand
draws and not forty thousand - 15 to 30 % bin to bin in the core.

Measured over twenty events the dump's z0 is Gaussian with sigma 50.1 mm from its
central 68 %, 49.6 from its 95 % and 52.0 from its 99.7 %; the model's fitted
50 mm gives 49.0 / 48.6 / 49.8. Against the reference's own scatter between four
disjoint five-event subsamples the model sits at **chi2/ndf = 0.49**.
`reference_scatter.py` is that check, for any field.

The one real difference is a hard truncation: the dump has no primary beyond
|z0| = 175 mm, the beamspot being generated within about 3.5 sigma, where the
model's Gaussian has no cut. Worth 0.3 % of the primaries.

## Two traps in the GNN4ITk dump

Both silently produce plausible-looking nonsense.

**Barcodes are not unique within an event.** They are unique only within one
pile-up interaction, and a dump event holds of order two hundred: in the sample
used here 85936 particles share only 3979 distinct barcodes. The particle key is
the `(Part_event_number, Part_barcode)` pair, and the cluster links carry both,
`CLparticleLink_eventIndex` and `CLparticleLink_barcode`. Keying on the barcode
alone merges particles across interactions and inflated the mean hit count from
9.7 to 113.8.

**Only generator particles carry a HepMC status.** `Part_status == 1` selects
final-state generator particles, but detector secondaries have no HepMC status at
all - theirs encodes the Geant4 process, with values running 20001, 100001,
120001 and so on. Applying the status cut to everything removes every secondary.

Primary versus secondary is `Part_barcode < 200000`, the usual Athena convention.
The dump agrees with it: the low-barcode particles are produced within a few mm of
the beam line, the high-barcode ones at a median radius of 160 mm.

## One trap in ColliderML

`perigee_d0` and `perigee_z0` are **NaN for a fifth of the charged particles above
100 MeV**, and the d0 sign convention is the opposite of the usual one. Both
loaders therefore compute the impact parameters from the production vertex and the
momentum, so the two detectors are compared against one definition. Where the
file's own values are finite they agree in magnitude.

Its `primary` column is an explicit generator/secondary flag, so no barcode
convention has to be reproduced. It means something narrower than the ITk dump's
`Part_barcode < 200000`: heavy-flavour decay products are secondaries here, which
is part of why the two d0 distributions look so different.

## What the rings cost, and what is still to do

Describing the endcaps ring by ring puts the ITk layout at 156 surfaces and the
ODD's at 33. Measured at a fixed space point count that costs **12 % more
generation time**, 39.0 ms against 43.7 ms: the per-surface work is one
intersection with an early exit, while producing a space point and its secondaries
is not. Cheap enough that there is no reason to offer the coarse layout as an
option.

The seeding benchmarks on the ITk layout:

| | efficiency | seeds | time | seeds before the sweep |
| --- | --- | --- | --- | --- |
| spherical grid | 99.8 % | 27.4k | 1.02 s | 34.0k |
| cylindrical grid | 100 % | 24.2k | 1.36 s | 30.3k |
| orthogonal k-d tree | 99.8 % | 23.1k | 4.93 s | 31.2k |
| GBTS | 94.2 % | 4.2k | 0.105 s | 4.8k |

The seed counts fell by about a fifth after the sweep and the efficiencies did not
move. That is the refitted endcap material showing up where a seeder feels it: the
same 220k space points now belong to 52k secondaries rather than 82k - all of
them, not the 300 MeV selection the tables above count - so fewer soft one-hit
tracks are scattered through the forward region making candidate pairs that go
nowhere. Generation got cheaper for the same reason, 73.3 ms against
89 ms on the ITk and 25.6 against 27 on the ODD.

A seed counts as true when three of its space points come from one primary, not
when all do. That is invisible for the triplet seeders, whose seeds are always
three space points, but GBTS returns four to eleven, and scoring it on every space
point matching costs it four points of efficiency that say nothing about the
seeder.

**Efficiency does not discriminate** on this event: a forward primary leaves
fourteen space points, and finding one true seed among those is easy for anything,
so compare the times and the candidate pair counts instead. **A GBTS connection
table belongs to a layout**: its reach along z has to cover the ring sets of the
endcap, since consecutive disks of a resolved endcap are not at consecutive radii.
And what GBTS still loses is the table rather than the cuts — its remaining 5 %
sits at the barrel-endcap transition, |eta| 1 to 1.5, where a hand-written table
is weakest. The ATLAS one is trained.

The GBTS cuts themselves are the ACTS defaults, which are what Athena runs on the
ITk pixel detector: `ActsTrk::GbtsSeedingTool` overrides only the connector file,
the ML lookup table and `minPt`, and its remaining defaults agree property by
property, tracking filter included. Two do not — `matchBeforeCreate` and
`nMaxEdges` — and one, `beamSpotCorrection`, is not read anywhere in
`Acts::Experimental::GraphBasedTrackSeeder`. None changes efficiency here;
`matchBeforeCreate` removes fakes and is worth 15 % of the run time.

### What each term is worth

`ablate.py` takes every term of the model out in turn and scores what is left, on
all nine figures at once - see `fit_event_config.FIGURES`. Judging on the spatial
shape alone is what makes this exercise go wrong: the terms trade against each
other, and dropping the transverse kick *improves* the shape threefold while
taking the impact parameter distribution it exists for from 0.52 to 5.5.

**The table below predates the 2026-08-01 sweep and has not been re-measured.**
Its scores are against the old presets, the old endcap profile and a `FIGURES`
without the production, pseudorapidity and secondary-hit terms, so read it for
which terms matter and not for the numbers. Re-running it is `--refit` at about
seven minutes a term.

Two measurements per term, and the second decides. The **quick** scan removes the
term and re-solves only the two normalisations, so it says what the term carries
where the fit currently sits. The **refit** runs the whole fit again without it,
so it says what survives once every other parameter has had the chance to absorb
it - and a term the rest of the model can absorb is a reparametrisation rather
than physics.

    ./ablate.py itk --fullsim <dump>.root            # seconds
    ./ablate.py itk --fullsim <dump>.root --refit    # ~7 min per term

Refitted, against a refitted baseline of 0.067/0.520 (ITk) and 0.085/0.902 (ODD):

| term removed | ITk shape | ITk \|d0\| | ODD shape | ODD \|d0\| | verdict |
| --- | --- | --- | --- | --- | --- |
| endcap material | **0.314** | 0.517 | **0.122** | 1.216 | keep, the largest term |
| path length | 0.079 | 0.554 | **0.135** | 1.101 | keep, ODD only |
| return branch | 0.058 | 0.631 | 0.085 | 1.144 | keep, for the primary hits |
| transverse kick | 0.018 | **5.472** | 0.056 | **5.847** | keep, \|d0\| is made of it |
| parent momentum | 0.084 | 0.529 | 0.102 | 0.972 | keep |
| momentum spread | 0.073 | 0.402 | 0.101 | 0.748 | keep, but it trades |
| decays | 0.059 | 0.658 | 0.083 | 0.945 | keep, weakly |
| secondary min pt | **0.049** | 0.518 | 0.072 | 1.042 | a guard, now at 5 MeV |
| *fixed fraction of parent* | 0.026 | 0.695 | 0.065 | 1.221 | the model this replaced |

Read against an event-to-event spread, measured over eight seeds of the untouched
preset, of 0.004 on the shape and 0.033 on |d0|. Nothing here is noise. The table
was measured before the collinear fraction was dropped, so the baseline it is read
against is the one with that term still in.

The compensation the fit reaches for says as much as the score. Without the
material term `secondaryRate` has to go from 0.180 to 0.301 and the shape still
ends up 4.7 times worse - nothing stands in for it. Without the path length term
on the ITk the rate goes to 0.300 too and the shape only reaches 0.079, because
the endcap material profile absorbs most of it; on the ODD, with far less endcap
to absorb into, the same removal costs 0.085 to 0.135. Strongly degenerate on the
ITk, clearly separate on the ODD, which is the argument for keeping both.

None of this is a runtime question: no term is worth more than about a tenth of a
whole event, and removing the secondary momentum floor makes generation 5 %
*slower*, which is what that floor is for.

#### Why there is no conversion component

There was a `secondaryCollinearFraction`, a share of secondaries given no
transverse kick, standing for photon conversions. It is gone. It had been set to
0.149, the share of the dump's secondaries born with kT below 10 MeV, which is the
wrong quantity for a model with no photons in it: a collinear daughter here stays
exactly on its parent for ever and inherits its d0, whereas a real conversion
electron is soft, curls, and acquires an impact parameter within a layer or two —
and it would follow the wrong parent anyway, the charged primary that crossed the
surface rather than the photon. At 0.149 the innermost decade of |d0| held 3.3
times the share of secondary space points the reference puts there.

Fitted to the |d0| profile instead, seed-averaged with the rate re-solved, both
detectors land independently on 0.02 — but zero fits as well:

| collinear | ITk \|d0\| | ODD \|d0\| |
| --- | --- | --- |
| 0.000 | 0.361 ± 0.009 | 0.364 ± 0.066 |
| 0.020 | 0.353 ± 0.026 | 0.345 ± 0.014 |
| 0.149 | 0.564 ± 0.042 | 1.026 ± 0.016 |

Since the profile only bounds it from above and the ordinary kicked secondaries
already fill that decade through curvature alone, the parameter was removed rather
than retuned. Refitted without it the presets give shape 0.075 / |d0| 0.377 on the
ITk and 0.092 / 0.358 on the ODD, against 0.067 / 0.520 and 0.085 / 1.035 before.

Use `solve_secondary_kick` and not a local search for anything scored on |d0|: one
event's mismatch varies by up to 0.04 between realisations at a fixed setting, so a
simplex contracts on noise and returns its starting point.

#### Where the ODD's hard secondaries come from, and where they do not

The earlier reading was that the ODD's hard secondaries are the transverse kick:
removing it drops the mean from 1.4 to 1.12, and the 0.31 GeV it stood at had been
measured on the ITk and carried over unchecked. That pointed at a per-detector kT.

It is not one. Fitted independently against ColliderML, with the pseudorapidity of
the secondaries in the objective alongside their |d0|, the ODD lands on
**0.267 GeV** - the ITk's fitted value to three digits, and its *measured* value
too. One kick, two detectors, two full simulations; the old 0.310 was a median
read as a scale, as above.

So the hard secondaries are still unexplained. The correction moved them from 1.42
to 1.40, and what is left is the shape of the model's secondary spectrum above
ColliderML's 100 MeV threshold rather than a parameter set wrong - `--fit-momentum`
reaches it and trades the non-primary shape for it, the sign of a shape the model
cannot make rather than a scale it has wrong.

Still to do:

- A **duplication probability per crossing** for module overlaps, which account
  for the whole remaining hits-per-primary deficit. Two space points close
  together on one layer is also what a real seeder has to cope with. Propagation
  rather than parameters, and it raises the space point count, so `secondaryRate`
  has to be re-fitted after it - one command, `fit_event_config.py`.
- A **material weight per ring** rather than per disc, for the factor 2.5 between
  the innermost and outermost radial band that nothing in `DetectorSurface` can
  express.
- **Re-measure `ablate.py`**, whose table predates this sweep in both the presets
  and the figures it scores.
- The **secondary pseudorapidity on the ITk**, 0.088 against 0.033 before, the one
  figure the sweep moved backwards and the only one where the ITk is now worse
  than the ODD.
