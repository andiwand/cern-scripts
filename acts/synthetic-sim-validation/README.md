# Validating the ACTS synthetic space point generator

`ActsFatras::Synthetic` is a deliberately coarse fast simulation that produces
space point events for seeding benchmarks. These scripts check that the
distributions it produces are in the right place, which is the only claim it
makes. Two of its three shipped layouts have a full simulation to be checked
against: the ITk against a GNN4ITk Athena dump, and the ODD against ColliderML.

## Running it

```sh
# one fast-simulation event per layout, written as two CSV files
ActsBenchmarkSyntheticEventGeneration --layout itk-pixel --runs 2 --warmup 0 \
    --dump /tmp/fastsim-itk
ActsBenchmarkSyntheticEventGeneration --layout odd-pixel --runs 2 --warmup 0 \
    --dump /tmp/fastsim-odd

# ITk, against a local GNN4ITk dump
./validate.py itk --fullsim ~/Downloads/user.avallier.*.DumpGNNITk_v9.root \
    --fastsim /tmp/fastsim-itk --events 5 -o plots

# ODD, against ColliderML ttbar at a pile-up of 200; the shard is downloaded
# from HuggingFace on first use and cached
./validate.py odd --fastsim /tmp/fastsim-odd --events 20 -o plots
```

Plots land in `plots/<detector>/` as PDF, so the two comparisons do not overwrite
each other; `--format png` if a raster is wanted instead. Everything is
normalised per event, so the two samples are comparable whatever number of events
each holds.

`fit_event_config.py <detector>` fits `ActsFatras::Synthetic::EventConfig` to a
reference and prints it as the C++ of a preset, which is where the numbers now in
`EventConfig::itkPixelTtbarPu200` and `EventConfig::openDataDetectorTtbarPu200`
came from.

### Layouts are read, not fitted

A geometry is a known thing and should not be fitted to simulated data. Each of
the three shipped layouts is read out of the authoritative description of its
detector, by one of two scripts that print the C++ to paste into
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
build there is nothing to transcribe and
`Python/Examples/tests/test_fatras_synthetic_layout.py` checks that the pasted
numbers still match the geometry. The ITk has no ACTS description, hence the XML.

Run these with `python <script>` rather than through the shebang: the shebang
picks up a different interpreter, and DD4hep then fails to find its plugins.

One loader per sample format - `fullsim_itk.py`, `fullsim_colliderml.py`,
`fastsim.py` - each producing the `sample.Sample` that `validate.py` plots, so
adding a third full simulation means adding one file.

### The ODD path needs pyarrow, which the ACTS environment breaks

`uproot`, `numpy` and `matplotlib` are all in the repository's
`requirements.txt`. ColliderML is Parquet, which needs `pyarrow`, and in the ACTS
spack environment importing it fails on a missing `_iconv`: spack's `libiconv`
shadows the macOS one that the wheel was built against. Taking spack's library
paths out of the environment for the run is enough, and nothing else in the
script needs them:

```sh
env -u DYLD_LIBRARY_PATH -u DYLD_FALLBACK_LIBRARY_PATH ./validate.py odd ...
```

This is the same breakage that makes `awkward` unusable there, which is why the
ITk loader asks uproot for `library="np"`.

## What the tuning fixed

The plots in `plots/` are of the tuned generator. Before it, the same comparison
ran on one set of ITk-flavoured parameters for both detectors, and the following
were wrong by more than the generator's own coarseness accounts for. Each entry is
the ratio of fast to full simulation, before and after.

| | before | after | what changed |
| --- | --- | --- | --- |
| space points / event, ODD | 1.26 | 1.00 | `chargedPerUnitEta`, `secondaryRate` |
| primaries / event, both | 1.26, 1.29 | 1.00 | `chargedPerUnitEta` 6.6 -> 5.1 / 5.3 |
| primaries above 10 GeV | 0.02 | 0.5 | `ptExponent` 11 -> 4.9 |
| mean primary pT | 1.05 | 0.99 | `ptScale` 4.7 -> 1.34 |
| d0 core width, ODD | 7.1 | 1.00 | `d0Sigma` 0.1 mm -> 0.014 mm |
| z0 core width, ODD | 0.77 | 1.00 | `beamspotSigmaZ` 45 -> 59 mm |
| mean secondary pT | 0.45 | 1.09 | `secondaryPtSlope` 0.15 -> 0.51 |

The single biggest one is the primary yield, and it is worth saying why it was
wrong. `chargedPerUnitEta = 6.6` is a real minimum-bias number, but it is the
density at *central* pseudorapidity, and the generator spreads it flat over
|eta| < 4 where the real distribution falls off forward. Both references say the
average over that range is 5.1 to 5.3: an ITk dump has 8.5k and ColliderML 8.5k
long-lived charged primaries per event above 100 MeV inside |eta| < 4, against the
10.6k a flat 6.6 produces.

Getting there needed one trap avoided. ColliderML's particle table also contains
charged *resonances* - rho+-, K*+-, Delta - which decay before any sensor: 43 % of
its charged primaries above 2 GeV leave no pixel cluster at all, and cutting on
long-lived species is what makes the count agree with the ITk dump's.

What tuning cannot fix is in the sections below, and it is one thing: how many
space points a primary leaves.

## ITk, on ttbar at a pile-up of 200

Five events of `DumpGNNITk_v9` against one generated event, after tuning.

| | full sim | fast sim | ratio |
| --- | --- | --- | --- |
| pixel space points / event | 219600 | 221400 | 1.01 |
| primaries / event | 8190 | 8192 | 1.00 |
| secondaries / event | 4760 | 26900 | 5.6 |
| mean primary pT | 0.60 GeV | 0.60 GeV | 0.99 |
| mean pixel hits, primaries | 9.7 | 8.7 | 0.90 |

Good:

- **Total space points per event**, and the profile in r and |z| that goes with it.
- **pT spectrum of the primaries**, now across the whole range rather than only
  the first few GeV: the tail reaches 30 GeV as the reference does.
- **z0** and **d0**, both Gaussians of the fitted width. The reference's d0 has a
  tail past 0.05 mm that the fast simulation does not; those are decay products
  that the generator makes as secondaries instead.
- **eta**, flat within the 13 % that the reference itself is flat to.
- **phi**, flat in both, and the space point azimuth with it.
- **Hits per particle against eta**, now in magnitude and not only in shape. Both
  rise from 5 to 6 in the barrel to a peak near |eta| = 3 of 14 to 15, and the
  fast simulation tracks the reference to within a few percent everywhere forward
  of |eta| = 1.5. This is what describing the endcap ring by ring bought: it was a
  uniform 64 % of the reference when the endcap was nine full-width disks.

Not so good:

- **Hits per particle are 10% low, and now only in the barrel.** The central
  plateau is 5.0 against 5.8; forward of |eta| = 1.5 the two agree. That residual
  is module overlap and nothing else — see the ODD section, where 1.26 times the
  five hits the fast simulation gives is the six the reference has, which accounts
  for the whole gap.
- **The primary/secondary split is wrong even though the total is right.** The
  generator makes six times too many secondaries, each with fewer hits, which is
  what lands the total space point count in the right place. Part of this is a
  genuine difference in bookkeeping rather than in physics: only about half of the
  real pixel clusters carry a truth link at all, while every synthetic space point
  belongs to a particle. So the real "unlinked" component has no counterpart in the
  fast simulation, and the surplus secondaries stand in for it. That is what
  `secondaryRate` is documented to absorb, and tuning it to the space point count
  makes the surplus larger, not smaller. It is a deliberate choice: the two cannot
  both be matched, and the space point density is what a seeder sees.

### The ITk endcap is rings, and describing them is what fixed the z distribution

The layout used to cover the endcap with nine full-width disks per side, and the
`z` distribution showed it: the fast simulation piled its endcap hits onto nine
positions while the full simulation was spread over the whole range. That was the
layout, not the tuning.

The endcap is 75 disks per side carrying 95 rings, and each ring is one module
deep — forty millimetres of radius out of the three hundred the detector covers.
So a track crossing a disk usually crosses no silicon, which nine full-width disks
cannot express. The nine sections, from `ITKLayouts/data/Pixel/*Defines.gmx`:

| section | r [mm] | \|z\| [mm] | rings |
| --- | --- | --- | --- |
| InnerBarrel L0, L1 | 34, 99 | to 244, 245 | cylinders |
| OuterBarrel L2-L4 | 160, 228, 291 | to 374.6 | cylinders |
| InnerEndcap L0 | 42.8 | 263-1142 | 15 |
| InnerEndcap E0 | 68.3 | 1103-1846 | 6 |
| InnerEndcap L1 | 100.1 | 263-2621 | 23 |
| OuterIncline L2-L4 | 168.5, 235.0, 297.4 | 397-1039 | 6, 8, 9 |
| OuterEndcap L2-L4 | 174.6, 234.7, 294.7 | 1146-2850 | 11, 8, 9 |

Two things fall out of this that are worth keeping.

The barrel is *short*, and correctly so. The outer three layers are flat only to
|z| = 374.6 mm and the inner two to 244 mm; beyond that the layer continues as
inclined rings, which Athena labels endcap. So a barrel that looks too short next
to the detector's overall length is the geometry, not a mistake.

And the reading is checkable. Grouping the dump's clusters by
(`CLbarrel_endcap`, `CLlayer_disk`, `CLeta_module`) resolves the same 95 rings,
and every ring position agrees with the XML to better than half a millimetre and
every radial extent to better than one. Resolving `CLeta_module` is what makes the
endcap intelligible: grouped by layer alone, a layer looks like a ring at fixed
radius spanning a metre of z, which is not something the model can express at all.

## ODD, against ColliderML ttbar at a pile-up of 200

`CERN/ColliderML-Release-1` on HuggingFace is the ODD's own full simulation -
Geant4 through Key4hep on the same geometry, digitised with ACTS geometric
channelisation at a 50 x 50 um pixel pitch - so a row of its `tracker_hits` table
is a cluster, which is what a space point generator produces. Twenty events of
`ttbar_pu200` against one generated event; only the pixel volumes 16, 17 and 18
are read.

| | full sim | fast sim | ratio |
| --- | --- | --- | --- |
| pixel space points / event | 101950 | 101640 | 1.00 |
| primaries / event | 8410 | 8416 | 1.00 |
| secondaries / event | 3970 | 15400 | 3.9 |
| mean primary pT | 0.63 GeV | 0.63 GeV | 1.00 |
| mean pixel hits, primaries | 6.2 | 5.0 | 0.80 |

The hits ratio is the one number the ODD refinement did *not* move, and that is
the useful part: 1.26 x 5.0 = 6.3 against the reference's 6.2, so module overlap
accounts for the whole of it, with nothing left over for the layout to explain.

### The layout is right to a millimetre

This is the one layout in the set that can be checked against a full simulation of
the same detector, and it comes out exact. Measured on the shard against
`openDataDetectorPixelDescription()`:

| | ColliderML | preset |
| --- | --- | --- |
| barrel radii [mm] | 32.5, 68.4, 114.3, 170.3 | 32.2, 68.2, 114.2, 170.2 |
| barrel half length [mm] | 507.2 | 507.25 |
| disk \|z\| [mm] | 618.8, 718.8, 838.9, 978.8, 1118.9, 1318.7, 1518.8 | 620.4, 720.4, 840.4, 980.4, 1120.4, 1320.4, 1520.4 |
| disk r [mm] | 42.0 ... 173.7 | 42.85 ... 173.79 |

The radii are means over the clusters of a layer, so a few tenths of a millimetre
is as close as this can come.

The r-z occupancy plot is the same picture twice. It also confirms the 1.8 mm
sensor offset the preset carries: the silicon is at 32.2 mm, not at the 34 mm
`OpenDataPixels.xml` declares.

#### An ODD endcap layer is two rings, staggered in z but not separated in r

`layout_from_geometry.py odd` resolves each of the seven endcap layers into two
disks rather than one: the ring at r = 42.85-110.95 mm sits 4.2 mm short of the
nominal layer z and the one at r = 105.52-173.79 mm 2.8 mm beyond it. Modelling
that stagger is all the ring structure buys here, and it is visible in the
occupancy plot as a small jog at r ~ 107 that both simulations now have.

What it does *not* buy is a radial gap, because there is none: the two rings
overlap by five millimetres, which is the module overlap of the real detector. So
the layout's previous two uniform rings over 42.85-173.79 mm were already right
about the radial coverage — they put the boundary at 108.3 mm where the geometry
puts the overlap centre at 108.2 mm. That is worth recording because it is the
opposite of the ITk, where the gaps carry most of the physics: a disk there is one
module deep out of three hundred millimetres of radius.

The overlap is also what makes resolving rings safe in general. Two z planes
covering the *same* radii are one ring whose modules alternate in z, not two
rings, and splitting those would give a track two space points where the detector
gives it one; the ITk pixel endcap staggers the halves of a ring by 6 mm, so this
is not hypothetical. `maxRingOverlap` is the discriminator, and it has to be
checked over every pair of planes rather than neighbours in z — the Generic
detector's strip endcap interleaves its rings, so the two halves of one ring can
have another ring between them.

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
  which is better than the 14 um a 50 um pitch gives digitally because its clusters
  are charge-weighted. Note the residual's *RMS* is 120 to 230 um - that is merged
  clusters, not resolution, and taking the RMS for the resolution would be wrong by
  an order of magnitude.

Not so good:

- **Barrel hits per particle are flat at exactly 4.0**, one crossing per cylinder,
  against 6.0 in the full simulation. This is the one mismatch no parameter
  reaches, and there are two separate effects behind it, both measured on the
  shard: module overlaps give **1.26 clusters per layer crossing** at every
  momentum, and soft tracks cross the same layers repeatedly - a primary at
  |eta| < 0.5 leaves 12.9 pixel clusters on average between 100 and 200 MeV, up to
  44, against 4.7 above 1 GeV. The synthetic helix takes one intersection per
  surface, so it cannot produce either. This is what the hits-vs-eta plot shows as
  a spike at eta = 0 in the full simulation and a plateau in the fast one, and it
  is why the barrel holds 40 % of the fast simulation's space points against 52 %
  of the reference's. Fixing it means changing the propagation - a duplication
  probability per crossing for the overlaps, more than one turn for the curlers -
  not the configuration.
- **Only two thirds of the real clusters belong to the population being
  compared.** Every ColliderML cluster carries a particle link, unlike the ITk
  dump, but 33% of them come from particles outside the generator's acceptance -
  below 100 MeV or beyond |eta| = 4. So the surplus secondaries stand in for a
  real component here too, just an identifiable one.
- **The two material scales are not constrained by either reference.** Fitting
  `materialRScale` and `materialZScale` to the space point profiles walks them off
  towards no dependence at all for a ten percent gain in an objective whose
  residual is the barrel deficit above, and it does not land twice in the same
  place, so `fit_event_config.py` leaves them alone unless asked with
  `--fit-scales`. Scaling them down with the detector, which is the obvious guess -
  the ODD pixel ends at 170 mm and 1520 mm against the ITk's 291 mm and 2800 mm -
  makes the agreement *worse* than leaving them at the ITk values.
- **d0 has a tail the generator does not.** 5.6 % of ColliderML's primaries have
  |d0| beyond 2 mm, and they are produced at a median radius of 28 mm: strange and
  heavy-flavour decay products that the dataset still labels primary. The generator
  makes those as secondaries, so `d0Sigma` is the width of the luminous region and
  nothing more. Widening it to cover the tail would count them twice.

## Two traps in the GNN4ITk dump

Both of these silently produce plausible-looking nonsense, so they are worth
knowing about before writing anything else against this format.

**Barcodes are not unique within an event.** They are unique only within one
pile-up interaction, and a dump event holds of order two hundred of them: in the
sample used here 85936 particles share only 3979 distinct barcodes. The particle
key is the `(Part_event_number, Part_barcode)` pair, and the cluster links carry
both, `CLparticleLink_eventIndex` and `CLparticleLink_barcode`. Keying on the
barcode alone merges particles across interactions and inflated the mean hit
count from 9.7 to 113.8.

**Only generator particles carry a HepMC status.** `Part_status == 1` selects
final-state generator particles, but detector secondaries do not have a HepMC
status at all - theirs encodes the Geant4 process, with values running 20001,
100001, 120001 and so on. Applying the status cut to everything removes every
secondary.

Primary versus secondary is `Part_barcode < 200000`, the usual Athena convention.
The dump agrees with it: the low-barcode particles are produced within a few mm of
the beam line, the high-barcode ones at a median radius of 160 mm.

## One trap in ColliderML

`perigee_d0` and `perigee_z0` are **NaN for a fifth of the charged particles above
100 MeV**, and the sign convention of the d0 is the opposite of the usual one.
Both loaders therefore compute the impact parameters from the production vertex
and the momentum instead, so that the two detectors are compared against one
definition. Where the file's own values are finite they agree in magnitude.

Its `primary` column is an explicit generator/secondary flag, so no barcode
convention has to be reproduced. Note that it means something narrower than the
ITk dump's `Part_barcode < 200000`: heavy-flavour decay products are secondaries
here, which is part of why the two d0 distributions look so different.

## What describing the endcaps cost, and what is still to do

Reading the layouts out of the geometry rather than approximating them took the
ITk layout from 24 surfaces to 156 and the ODD's from 19 to 33. Measured on the
same build at the same space point count, the ITk one costs **12 % more generation
time**, 39.0 ms against 43.7 ms: the per-surface work is one intersection with an
early exit, while producing a space point and its secondaries is not. What the
12 % buys is 41 % more space points from primaries and 40 % fewer stand-in
secondaries, and `secondaryRate` more than halved, 0.584 to 0.267.

It also moved every seeding benchmark, all measured on the ITk layout:

| | before | after |
| --- | --- | --- |
| spherical grid | 89.6 % / 0.79 s | 99.8 % / 1.06 s |
| cylindrical grid | 86.0 % / 1.04 s | 100 % / 1.31 s |
| orthogonal k-d tree | 79.9 % / 3.6 s | 99.8 % / 5.4 s |
| GBTS | 72.6 % / 0.272 s | 90.8 % / 0.106 s |

Two things to take from that. **Efficiency has stopped discriminating**: a forward
primary now leaves fourteen space points, and finding one true seed among those is
easy for anything, so "at least one true seed" saturates. Compare the times and the
candidate pair counts instead, and use a harder measure if efficiency is the
question. And **a GBTS connection table belongs to a layout**: the table's original
reach of one or two disks along z was written for nine disks per side, and against
seventy-five it connected rings no track crosses in sequence while missing the ones
it does — 41.6 %. Widening the reach to nine, one per ring set, gave 90.8 %.

Still to do, both propagation rather than parameters, and both now the same single
mismatch — the barrel:

- A **duplication probability per crossing** for module overlaps, which the ODD
  reference measures at 1.26 clusters per barrel layer crossing, flat in momentum,
  and which accounts for the entire remaining hits-per-primary deficit. Two space
  points close together on one layer is also what a real seeder has to cope with,
  so this is worth having for its own sake.
- **More than one turn** in the helix propagation, so that soft tracks re-cross the
  layers they curl back through. Below 300 MeV the reference has two to three times
  the clusters per particle that one crossing per surface can give.

Both would raise the space point count, so `secondaryRate` has to be re-fitted
after either - which is one command, `fit_event_config.py`.
