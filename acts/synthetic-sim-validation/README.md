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

`fit_event_config.py <detector>` fits `ActsFatras::Synthetic::EventConfig` to a
reference and prints it as the C++ of a preset, which is where
`EventConfig::itkPixelTtbarPu200` and `EventConfig::openDataDetectorTtbarPu200`
came from. The two shipped presets are

```sh
./fit_event_config.py itk --fullsim '<dump>*.root' --events 50 \
    --path-length 4 --turns 1 --fit-kick --set secondaryKt=0.25 \
    --set stubRate=1.267 --set stubClusters=2.1 --set stubReach=4.0
./fit_event_config.py odd --events 50 --path-length 4 --turns 2 \
    --fit-kick --set secondaryKt=0.25 \
    --set stubRate=1.800 --set stubClusters=2.1 --set stubReach=4.0
```

Fifty events either side, the same number the validation gets, and the two halves
disjoint: `--events 50` takes the front of each ITk file and the front of the ODD
shard, `--events 50 --skip-events 50` in `validate.py` takes what follows. Fewer
is a false economy - the reference reduction is cached, so a bigger one is paid
once, while a primary multiplicity that swings ten percent event to event puts
4.6 % on `chargedPerUnitEta` fitted to five events against 1.4 % fitted to fifty.
The stub channel and the kick have to be passed in because they are measured
elsewhere and this fit does not touch them; left out they would silently go to
zero and to the fit's own answer.

The kick is pinned because it is measured, and because `--fit-kick` scored on
|d0| and |eta| alone runs it to the top of whatever grid it is given: a wider
kick throws daughters further out, which is the end of the |d0| distribution the
radial component does not fill, and it pays for that in a secondary momentum
nothing in that objective sees. Left free on the ODD it lands on 0.48 and takes
the mean secondary momentum from 1.05 to 1.69 times the reference's. With it
pinned, `--fit-kick` fits `secondaryRadialFraction` alone.

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
| the same, in r | the *ring* weights of the layout, `applyRingMaterialWeights` |
| shape of the non-primary space points in \|z\| | both of those, weakly -- see below |
| **secondary \|d0\| in its innermost decades** | `secondaryRadialFraction` |
| secondary \|d0\| in its outermost, and \|eta\| | `secondaryKt`, against the longitudinal momentum |

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
last column is the shipped preset before the sweep of 2026-08-01 (second pass),
on the same five reference events; the mismatches are averaged over five seeds.

| | full sim | fast sim | ratio | before the second pass |
| --- | --- | --- | --- | --- |
| pixel space points / event | 219648 | 219870 | 1.00 | 1.00 |
| &nbsp;&nbsp;primary | 87529 | 74064 | 0.85 | 0.85 |
| &nbsp;&nbsp;non-primary | 132119 | 145806 | 1.10 | 1.11 |
| primaries / event | 8191 | 8192 | 1.00 | 1.00 |
| **secondaries / event above 300 MeV** | 4761 | 10821 | **2.3** | 4.4 |
| mean primary pT | 0.60 GeV | 0.60 GeV | 0.99 | 0.99 |
| mean pixel hits, primaries | 9.7 | 9.0 | 0.93 | 0.93 |
| mean pixel hits, secondaries | 4.2 | 3.8 | 0.92 | 0.88 |
| secondaries born inside the beam pipe | 8.6 % | 8.8 % | 1.02 | 0.99 |
| **non-primary shape mismatch** | | **0.017** | | 0.035 |
| **secondary production \|z\| mismatch** | | **0.024** | | 0.085 |
| **secondary \|d0\| mismatch** | | **0.041** | | 0.219 |
| **secondary \|eta\| mismatch** | | **0.038** | | 0.088 |
| mean secondary pT | | | 0.88 | 1.04 |

Everything moved the right way except the mean secondary momentum, which is now
12 % low where it used to be 4 % high. That one is a shape the model cannot
make rather than a scale it has wrong -- see the second pass below.

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
- **Where the secondaries are made**, now to within 8 % in every band of |z|
  except the outermost, and the number of space points each leaves, 3.8 against
  4.2. Both come from the endcap material profile, and from the ring weights
  within it.
- **The impact parameter of the secondaries**, whose mismatch fell by a factor
  five once a share of them was emitted radially rather than off their parent.
  The share of their space points below 1 mm is 0.11 against the reference's
  0.14, having been 0.06.

Not so good:

- **The mean secondary momentum is 12 % low.** The corrected momentum law is
  right in the population and wrong in the tail: the reference's log-normal
  width *grows with the parent*, from half an e-fold at half a GeV to two at
  forty, and `secondaryMomentumSpread` is one number. Above the reference's
  300 MeV threshold the model therefore runs out of hard daughters. Making the
  spread a function of the parent momentum, as the median already is, is the fix.
- **Hits per particle are 7 % low, and only in the barrel.** The central
  plateau is 5.4 against 5.8; forward of |eta| = 1.5 the two agree. The residual
  is module overlap and nothing else, measured on the ODD shard below.
- **Twice too many secondaries above the threshold**, down from four times.
  What is left is bookkeeping rather than physics: only about half the real pixel
  clusters carry a truth link at all, while every synthetic space point belongs
  to a particle, so the real "unlinked" component has no counterpart and the
  surplus secondaries stand in for it. The ODD settles this - see below, where
  the reference links everything and the model has 1.26 times its secondaries
  rather than three times.

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

| | full sim | fast sim | ratio | before the second pass |
| --- | --- | --- | --- | --- |
| pixel space points / event | 101954 | 100962 | 0.99 | 1.01 |
| &nbsp;&nbsp;primary | 56772 | 45795 | 0.81 | 0.81 |
| &nbsp;&nbsp;non-primary | 45182 | 55167 | 1.22 | 1.26 |
| primaries / event | 8413 | 8416 | 1.00 | 1.00 |
| secondaries / event above 100 MeV | 3970 | 12027 | 3.0 | 3.7 |
| &nbsp;&nbsp;**over the whole spectrum** | **12502** | **15690** | **1.26** | 1.29 |
| mean primary pT | 0.63 GeV | 0.63 GeV | 1.00 | 1.00 |
| mean pixel hits, primaries | 6.2 | 5.4 | 0.88 | 0.88 |
| mean pixel hits, secondaries above 100 MeV | 4.1 | 3.3 | 0.81 | 0.82 |
| &nbsp;&nbsp;over the whole spectrum | 3.6 | 3.5 | 0.97 | 0.97 |
| **mean secondary pT** | | | **1.05** | 1.40 |
| secondaries born inside the beam pipe | 2.3 % | 2.3 % | 1.01 | 0.98 |
| **non-primary shape mismatch** | | **0.064** | | 0.077 |
| secondary production \|z\| mismatch | | 0.128 | | 0.128 |
| **secondary \|d0\| mismatch** | | **0.123** | | 0.270 |
| secondary \|eta\| mismatch | | 0.016 | | 0.022 |

**The two rows measured over the whole spectrum are the ones to read**, and they
are the reason this reference is worth more than the ITk dump: every ColliderML
cluster carries a particle link, so the reference's *whole* secondary population
can be counted rather than the selection above a truth-link threshold. Counted
that way the model has 1.26 times the reference's secondaries and gets their
cluster count right to 3 %. The 3.0 above it is the same population seen through
a 100 MeV cut that two thirds of the reference's secondaries fall below - see
the second pass.

The mean secondary momentum was 1.40 before and is the thing the second pass
moved most here.

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

## The second pass of 2026-08-01, on the secondaries alone

Four things, and three of them are the same mistake as the first pass in a new
place: **a quantity measured correctly through a selection, and then read as a
property of the population.** The selection is the truth-link threshold - the
momentum above which a full simulation records a secondary at all, a hard
300 MeV on the ITk dump and the loader's own 100 MeV on ColliderML.

### The secondary surplus was mostly the threshold, and the ODD proves it

Every ColliderML cluster carries a particle link, so its *whole* secondary
population can be counted rather than the part above a threshold. Per event, with
no momentum and no acceptance cut:

| | reference | model | ratio |
| --- | --- | --- | --- |
| non-primary particles with a cluster | 12502 | 16183 | **1.29** |
| ... above 100 MeV, \|eta\| < 4 | 3970 | 14796 | 3.73 |
| ... below 100 MeV | 7932 (63 %) | 1121 (6.9 %) | 0.14 |
| mean clusters per secondary | 3.61 | 3.50 | **0.97** |

So the model never had four times too many secondaries; it had 29 % too many,
and their momentum spectrum in the wrong place. Two thirds of the reference's
secondaries sit below the cut the fit compares over, against 7 % of the model's,
and `sec hits` of 0.83 is the same artefact - above 100 MeV the reference reaches
4.13 clusters per secondary because 20-50 MeV curlers pull it up, while over the
whole population it is 3.61 against the model's 3.50.

Its softest component is not modellable here and does not need to be: 5572
secondaries per event below 5 MeV, leaving 2.15 clusters each essentially where
they were made, 27 % of the non-primary cluster budget. That is the irreducible
part of the surplus, and it is a quarter rather than a factor four.
`secondaryMinPt` stays at 5 MeV: 1, 5 and 20 MeV are indistinguishable on all
nine figures and 50 MeV is clearly worse.

### The momentum law was measured through the threshold, and was a factor two out

`measure_secondary_kinematics.py` equated the observed per-bin median of the
daughter's longitudinal momentum with the underlying one. The dump's secondary
spectrum has a factor-15 density step at exactly 0.300 GeV, and the cut removes
45 to 50 % of daughters at *every* parent momentum - survival is 0.52 at a parent
of 0.5 GeV and 0.50 at 45 GeV, because a hard parent is forward and its
daughter's `sin(theta)` is small, cancelling the harder `pL`. There is therefore
no region of parent momentum where the cut is negligible and the law can be read
off directly.

Two truncation-aware estimators agree: a maximum likelihood whose per-secondary
likelihood is divided by its own survival probability, and a forward fold that
pushes a proposed law through the cut and compares the *surviving* medians with
the dump's. And ColliderML, which has parent links and no threshold, measures the
same law directly and needs no correction at all:

| | shipped | ITk, truncation-aware | ODD, measured directly |
| --- | --- | --- | --- |
| `secondaryMomentumScale` | 0.510 | **0.271 +- 0.006** | 0.220 |
| `secondaryMomentumExponent` | 0.567 | 0.62 +- 0.04 | 0.558 |
| `secondaryMomentumSpread` | 1.81 | 1.24 +- 0.09 | 1.60 |
| `secondaryKt` | 0.267 | 0.21 +- 0.04 | ~0.20 |

The forward fold is the proof: through the same cut, the shipped law predicts an
observed median `pL` of 3.12 GeV at a 10 GeV parent where the dump has 1.57, and
its objective is 0.639 against 0.166 for the corrected one. Both presets carry
the ITk numbers, the ODD's being the cross-check - how an interaction shares
momentum out is not a property of the detector watching it.

What the correction cannot reach, and what is behind the ITk's mean secondary
momentum of 0.88: **the spread grows with the parent**, the dump's observed
half-spread in log `pL` running 0.56 at a parent of 0.5 GeV to 2.08 at 45 GeV.
Truncation accounts for part of that rise and not its range, and one
`secondaryMomentumSpread` folded through the cut only spans 0.95 to 1.35. Also
inaccessible: **11 % of the dump's secondaries have negative `pL`**, i.e. are
emitted backwards, which a log-normal drawn positive cannot produce.

### Half the secondaries have a *neutral* parent, and that is what makes \|d0\| broad

The |d0| mismatch was the worst figure on both detectors, 0.219 and 0.270, and no
setting of any existing parameter moved it: scanning the kick, the momentum
scale, the spread, `secondaryMinPt`, `maxTurns`, the path length and every
material handle, the 0.1-1 mm decade never exceeded 0.072 against the reference's
0.131.

On the dump's parent links, 49.5 % of secondary space points come from a daughter
whose parent is **neutral**, and half of those are emitted with a transverse kick
below 30 MeV. The kick is Rayleigh(0.267) exactly above 0.2 GeV; what it is
missing is a **delta at zero**, not a wider tail - P(kT < 10 MeV) is 23.6 % of
the hit weight against 0.07 % for a Rayleigh.

Those daughters are **radial**. Their neutral parent - a converted photon or a
neutral hadron - is born at r = 0, does not bend, and leaves nothing on the way,
so the daughter's |d0| is its own curvature alone. Median |d0| against `r^2/2R`,
band by band in production radius, with no free parameter:

| production r [mm] | median \|d0\| | `r^2/2R` |
| --- | --- | --- |
| 0-25 | 0.366 | 0.368 |
| 25-50 | 0.775 | 0.751 |
| 50-100 | 4.515 | 4.352 |
| 100-200 | 11.464 | 11.087 |
| 200-400 | 38.227 | 38.859 |

The reference's charged-parent half alone is 0.004 / 0.033 / 0.203 / 0.651 /
0.109 by decade, which is what the model already made (0.009 / 0.050 / 0.249 /
0.627 / 0.065). It described the half it modelled and had no representation of
the other half.

`EventConfig::secondaryRadialFraction` is that share, fitted to **0.25** (ITk)
and **0.20** (ODD). It is not the `secondaryCollinearFraction` that was removed,
and the three arguments that removed it are each answered by measurement:

- *"a collinear daughter stays exactly on its parent and inherits its d0"* - true
  of the removed parameter, which followed the **charged** parent, whose bend
  `r^2/2R_parent` cancels the daughter's whenever the charges agree, dumping
  everything into the innermost decade. The real parent is neutral 98.4 % of the
  time, so there is nothing to cancel.
- *"it would follow the wrong parent anyway"* - exactly so, and that is what this
  corrects. The right parent came straight from the beam line, so the daughter is
  radial and the photon never has to be simulated; the charged primary's crossing
  is only a proxy for where the material is.
- *"at 0.149 the innermost decade held 3.3 times the reference's share"* -
  reproduced if the radial direction is given to the decay branch as well, which
  is why it is applied to surface secondaries only.

A parent-link-free signature confirms the same component on the ODD, where no
parent links were used: the share of secondary hit weight with |d0| within a
factor 1.6 of `r^2/2R` is 25.6 % (ITk reference) and 34.2 % (ODD reference)
against 4 % in the model, and 4 % is the accidental floor - the ITk's
collinear-neutral-parent set sits at 91.7 % and both other populations at 4-5 %.

**The kick has to be pinned once this exists.** Free, and scored on |d0| and
|eta|, it runs to the top of any grid: with the radial component filling the
small-|d0| end, the only thing left for the kick to fix is the far end, and it
buys that with a secondary momentum the objective does not see. On the ODD it
lands on 0.480 and takes the mean secondary momentum to 1.69.

### An endcap disc's material is spread across it, not just along z

`materialWeight` was a property of a `DetectorSurface`, i.e. of a whole disc,
while `implied_material.py` shows the outermost ring set of the ITk endcap asking
for about three times the weight of the ones inboard of it, at every |z|. It is
not a gradient and no power of r stands in for it - fitted, the ITk asks for
`(r/150)^+0.25` and the ODD for `^-0.25`, both indistinguishable from zero.

`RingBounds` and `DetectorLayer` now carry a `materialWeight` of their own, which
`applyRingMaterialWeights` fills from radial bands. The ITk's six ring families
take **1.50 / 0.70 / 0.50 / 1.50 / 0.50 / 1.50**. Against a **held-out reference**
- five events of a different dump file, which the fit never saw - that is worth

| | shipped, flat | with ring weights |
| --- | --- | --- |
| shape + prod z | 0.1058 | **0.0495** |
| secondary production \|z\| | 0.0721 | **0.0186** |
| secondary \|d0\| | 0.2020 | 0.1727 |
| mean secondary hits | 0.880 | 0.933 |

and it costs no CPU: the ITk layout still has 156 surfaces and generation still
takes 77 ms an event. `(250, 1.20)` is still the endcap optimum with the ring
weights in place, over the full 36-point grid.

**The ODD asks for no radial term** - fitted freely, all its bands land on 1.00 -
and instead wants **barrel** weights, `{0.70, 0.70, 1.00, 2.20}`, worth 0.196 to
0.184 on the joint objective and 0.223 to 0.160 on |d0| against its own held-out
reference. The ITk's barrel weights are worth nothing once the rings are free
(held out, 0.1058 to 0.1067) and were standing in for endcap radial structure.
The two detectors are opposite: the ITk's residual material is endcap-radial, the
ODD's is barrel.

Two things this still cannot express: the **beam pipe** is a passive cylinder
pinned at weight 1, and the ITk reference makes 8.8 % of its secondary hit weight
in the beam pipe wall at r = 20-24 mm against the model's 0.4 %; and the ODD's
implied table wants structure in |z| *within* a barrel cylinder, 0.57 below
|z| = 250 against 1.75 from 250 to 507, which one weight per cylinder cannot say.

### `sec eta` is not a material problem

The ITk's secondary pseudorapidity, the figure the first pass moved backwards, is
0.038 now, and the corrected momentum law rather than any material term is what
recovered it. A radial material term does move it the predicted way - more weight
at large r puts the parents at lower |eta| - but the radial profile the
production figure asks for is not monotonic in r and leaves it where it was, and
every |z| profile that recovers the old 0.033 costs the objective a factor five.

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

## Module overlap

`measure_overlaps.py` reads the overlap off the dump's own module identifiers
rather than off a distance cut, so a second cluster on a layer is an overlap when
it is on a neighbouring module and a re-crossing otherwise. Above a GeV:

| | extra clusters per crossing | stagger |
| --- | --- | --- |
| ITk barrel layer 0 | 0.02 | 7.9 mm in r |
| ITk barrel layers 1-4 | 0.13 - 0.16 | 7.9 mm in r |
| ITk endcap, per ring crossed | 0.15 - 0.19 | 5 mm in z |
| ODD, everywhere | 0.24 | 1.65 mm in r, 1.2 mm in z |

Two things this settles. The rate is **flat**: one number per detector covers it,
and the ITk endcap only looks different because one `layer_disk` index there
carries a quarter-shell of rings. And the pair is staggered along the surface
**normal**, not around in phi - adjacent staves alternate in radius and the
overlap is that alternation seen edge on, the |r*dphi| between two clusters of a
pair being 0.24 mm against 7.9 mm in r. So a model that only duplicates a hit
produces something a seeder will deduplicate; the offset is the whole point.

Following the track through that offset reproduces the rest of the geometry for
free: the endcap's measured 1.83 mm in r against 6.00 mm in z is the track's own
slope, not a second parameter.

`DetectorSurface::overlapProbability` and `::overlapOffset` carry it,
`EventConfig::overlapScale` turns it up or down. It costs 4 % of the generator's
CPU (ITk 67.5 to 70.4 ms per event, ODD 22.7 to 24.8).

What it bought, fitted on fifty events and scored on fifty it never saw:

| | before | after |
| --- | --- | --- |
| ITk mean hits per primary | 0.89 | **1.01** |
| ITk non-primary space points | 1.09 | **1.00** |
| ITk primary space points | 0.79 | 0.88 |
| ODD mean hits per primary | 0.86 | **1.05** |
| ODD non-primary space points | 1.27 | **1.04** |
| ODD primary space points | 0.79 | **0.96** |
| ODD space points per event | 1.00 | **1.00** |

The non-primary column is the one to read. It had been carrying the primary
clusters the layout could not make, which is why it ran a tenth to a quarter high
while the primaries ran a fifth low; both are now within a few percent of one.

## The primary column has an acceptance in it

A cluster counts as primary from its truth link alone, with no cut on the
particle, while the "mean hits" row applies the generator's own p_T and eta
acceptance. So the two rows are over different populations, and the difference is
not small: **8463 clusters per ITk event and 4537 per ODD event - a twelfth and a
twentieth of each primary column - come from a primary below `minPt` = 100 MeV or
beyond `maxEta` = 4**, which the generator is configured never to produce. Split
out, the primary column reads

| | reference | model | ratio |
| --- | --- | --- | --- |
| ITk, in the acceptance | 89803 | 86036 | 0.96 |
| ITk, outside it | 8463 | 0 | 0.00 |
| ODD, in the acceptance | 49931 | 52396 | 1.05 |
| ODD, outside it | 4537 | 0 | 0.00 |

so inside the acceptance the model is within a few percent and on the ODD it is
*over*, not short. `validate.py` prints those two rows under the primary count.

The total is left alone deliberately, here and in the fit: a seeder meets every
cluster the detector makes, so the occupancy is what has to be reproduced and
taking any of it out would leave a generated event thinner than a real one. The
consequence is that `secondaryRate` stands in for those clusters too - the fit
solves it so that primary plus secondary hits reach the reference's whole count -
and at 3 % of all space points it carries roughly 5 % that is not secondaries.
`Target.unaccepted_space_points` records it. Read the fitted rate accordingly.

The clean fix is to widen the generator's acceptance rather than to narrow the
comparison, and it is not free: sub-100-MeV primaries curl, `maxTurns` = 1 cannot
follow them, and the reference's clusters per particle falls from 10.6 at
100-200 MeV to 8.2 above 3 GeV where the model is flat at 9.8.

### What the unaccepted clusters are

Measured on five ITk events, of 7835 unaccepted primary clusters per event:

| | particles/ev | clusters/ev | share |
| --- | --- | --- | --- |
| primaries below 100 MeV | 579 | 5905 | **75 %** |
| primaries beyond \|eta\| = 4 | 384 | 1924 | 25 % |

The soft ones are **curlers**, and not a faint version of a normal track: 10.2
clusters each over only **3.3 distinct layers**, a median of 5 on the busiest
one, 84 % revisiting a layer. Every one starts at r = 33 mm, 78 % of the clusters
sit inside r = 130 mm, and the median z spread is **1236 mm** - a tight spiral
(R = pT/0.6 mm, so 83 mm at 50 MeV) threading along the beam pipe. The high-|eta|
quarter is ordinary tracks, median |eta| 4.11 and 99 % below 4.29.

Standing in for them with secondaries is wrong in *shape*, not only in label:

| r [mm] | low-pT primary | secondary |
| --- | --- | --- |
| 0-40 | 18.7 % | 6.1 % |
| 40-80 | 22.7 % | 11.3 % |
| 80-130 | 36.7 % | 27.3 % |
| 130-200 | 13.4 % | 22.7 % |
| 200-300 | 7.8 % | 27.9 % |

So 2.4 % of all space points sit several layers too far out, in the region seed
combinatorics is most sensitive to.

### The spectrum was missing its Jacobian

`samplePt` drew `dN/dpT ~ (1 + pT/s)^-n`. The Hagedorn spectrum is the
*invariant* one, `dN/dpT ~ pT (1 + pT/s)^-n`, the leading `pT` being the phase
space Jacobian. Fitting both to the reference over 0.12-8 GeV and extrapolating
below it:

| | chi2/ndf in the fitted range | particles/ev below 100 MeV |
| --- | --- | --- |
| `(1 + pT/s)^-n` | 27.7 | 1977 |
| `pT (1 + pT/s)^-n` | **4.2** | **823** |
| reference | - | **538** |

The old form is 3.7x over below the threshold *and* 6.6x worse inside the range
it was fitted in, where it runs away to s = 4.8 GeV, n = 12.6 faking a turnover
it cannot produce. That is the same defect as the known excess at 100-200 MeV
seen from below. Fixing it is what makes a lower `minPt` possible at all.

The survival function does not invert, so `samplePt` solves it in five
safeguarded Newton steps, exact to 6e-8 and so better than float. The
distribution is a beta prime with shapes 2 and `n - 2` and could be drawn
exactly as a ratio of gamma variates, but every exact method rejects, and a
variable number of draws per track would put two platforms on different events.

### A stiff track was crossing the barrel twice

The helix meets every barrel radius a second time on the way back in, and
nothing rejected it: `maxTurns` bounds the turning angle and the layout has no
outer edge. At |eta| < 0.15 a stiff track carried 6.27 hits against 5.56 at
|eta| 0.3-1.0. `DetectorLayout::escapeRadius` and `escapeHalfZ` stop a track
where it leaves the tracker and the bin falls to 5.52, flat with its neighbours.

The bound is the **enclosing** tracker, not these pixel-only layouts: a 300 MeV
track turns on 500 mm, arcs out to a metre through the strips and curls back
into the pixels, so cutting at the pixel radius would delete real hits. 1000 mm
and 3050 mm for the ITk, 1100 mm and 3000 mm for the ODD. It is also what lets
`maxTurns` be raised for curlers without costing anything on tracks that cannot
curl - a stiff track now stops at its radial exit instead of looping.

### Generating the soft primaries: what it bought and what it cost

`minPt` 0.02 GeV, `|eta|` to 4.3, `maxTurns` 3, on fifty held-out events:

| ITk | before | after |
| --- | --- | --- |
| space points/event | 0.95 | 0.95 |
| &nbsp;&nbsp;primary | 0.88 | **1.00** |
| &nbsp;&nbsp;non-primary | 1.00 | 0.91 |
| secondaries/event | 1.50 | **1.06** |

| ODD | before | after |
| --- | --- | --- |
| space points/event | 1.00 | 1.01 |
| &nbsp;&nbsp;primary | 0.96 | 1.09 |
| &nbsp;&nbsp;non-primary | 1.04 | 0.90 |
| secondaries/event | 1.28 | 0.88 |

The ITk total does not move at all - the model shifts 12000 clusters/event out
of the non-primary column into the primary one, which is where they belonged.
`secondaryRate` falls with them, 4.762 to 3.048 (ITk) and 5.749 to 3.503 (ODD),
and it is no longer standing in for anything. That is the whole point: the
composition is now honest, and the residual deficit sits where it really is.

**What is left is a low-pT overshoot.** The generator makes **1.74x** too many
sub-100-MeV primaries, each leaving 0.85x the clusters, so 1.47x in clusters:

| pT [MeV] | reference/ev | model/ev | ratio |
| --- | --- | --- | --- |
| 20-40 | 70.6 | 162 | 2.29 |
| 40-60 | 118.4 | 237 | 2.00 |
| 60-80 | 168.0 | 285 | 1.70 |
| 80-100 | 202.4 | 321 | 1.59 |

Raising `minPt` does not fix it - the excess runs across the whole band rather
than piling up at the bottom. It is the invariant form over-extrapolating below
the range it was fitted in, and the fix is to **fit the spectrum over reference
particles below 100 MeV**, which both loaders can produce (`min_pt_mev`) and
which is currently thrown away. No third parameter needed, just data already on
disk. The forward tail is the smaller half of the same story, 1.15-1.25x over
because the eta density is flat where the real one falls to about 60 % of
central by |eta| = 4.3; a taper would fix that one.

Cost, measured back to back with the fitted presets: **ITk +8 %** (75.8 to
81.8 ms/event), **ODD -10 %** (26.2 to 23.5). The escape bound pays for most of
the extra turns.

## How many events the split needs

The primary multiplicity of a ttbar pu200 event swings **9 to 11 % event to
event**, so N events fix `chargedPerUnitEta` to about 10/sqrt(N) percent. Five
events, which the ITk preset used to be fitted on, is 4.6 %; fifty is 1.4 %. That
was worth more than anything else measured here.

Both halves are also spread over the ten dump files rather than taken from the
front, `fullsim_itk.load` giving each file its share of `--events` and
`--skip-events`. The files are separate Athena jobs and their means differ, but
by 3.2 % where the per-event spread alone predicts 3.1 %, so this is insurance
rather than a correction. There is no ordering structure within a file either -
blocks of fifty consecutive events run 9105, 9576, 9176, 9046, 9277 primaries
against errors of +-130.

So what is left of the ITk's primary count, 0.95, is those two particular blocks
disagreeing by 2.6 sigma. It is sampling, not the model. The ODD cannot do better
than fifty and fifty, its shard holding a hundred events, and does not need to;
the ITk has five hundred, so a 250/250 split would take each half to +-0.6 %.

Still to do:
- **A secondary momentum spread that grows with the parent**, as its median
  already does. One number cannot span the reference's 0.56 to 2.08, and that is
  the whole of the ITk's mean secondary momentum of 0.88.
- **A backward branch for the secondary momentum**: 11 % of the dump's daughters
  are emitted with negative longitudinal momentum and a log-normal cannot be.
- **Material on the beam pipe and along a barrel cylinder.** The ITk reference
  makes 8.8 % of its secondary hit weight in the beam pipe wall against the
  model's 0.4 %, and the ODD wants a barrel cylinder weighted differently at
  |z| < 250 than beyond it. `barrelModules` already splits a cylinder into eta
  modules, so the layer weight added here would reach the second.
- **Re-measure `ablate.py`**, whose table predates both passes in the presets, the
  figures it scores and the terms it can remove - there is now a radial share and
  a ring weight to ablate.
