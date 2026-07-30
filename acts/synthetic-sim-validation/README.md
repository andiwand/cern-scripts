# Validating the ACTS synthetic space point generator

`ActsFatras::Synthetic` is a deliberately coarse fast simulation that produces
space point events for seeding benchmarks. These scripts check that the
distributions it produces are in the right place, which is the only claim it
makes.

## Running it

```sh
# one fast-simulation event, written as two CSV files
ActsBenchmarkSyntheticEventGeneration --runs 2 --warmup 0 --dump /tmp/fastsim

# compare against an ITk full-simulation dump
./validate.py itk \
    --fullsim ~/Downloads/user.avallier.*.DumpGNNITk_v9.root \
    --fastsim /tmp/fastsim --events 5 -o plots
```

`fit_itk_layout.py <dump>` reports the layer structure the dump actually has,
which is how the findings about the ITk endcap below were arrived at.

Everything is normalised per event, so the two samples are comparable whatever
number of events each holds. Requires `uproot`, `numpy`, `matplotlib` - all in
the repository's `requirements.txt`. The ACTS spack environment works too, except
that `awkward` is unusable there because its `pyarrow` is broken, which is why the
loader asks uproot for `library="np"`.

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

## What agrees, on ttbar at a pile-up of 200

| | full sim | fast sim | ratio |
| --- | --- | --- | --- |
| pixel space points / event | 213500 | 197800 | 0.93 |
| primaries / event | 7960 | 10560 | 1.33 |
| secondaries / event | 4550 | 26120 | 5.75 |
| mean primary pT | 0.6 GeV | 0.6 GeV | 1.07 |
| mean pixel hits, primaries | 9.7 | 6.2 | 0.64 |

Good:

- **Total space points per event**, to 7%. This is the number the generator's
  `secondaryRate` was tuned to, and it holds.
- **pT spectrum of the primaries.** The Hagedorn-like form matches the full
  simulation from 200 MeV to about 5 GeV to within a few percent. It falls short
  above 8 GeV, where the generator's tail runs out.
- **z0**, a Gaussian of the right width.
- **phi**, flat in both, and the space point azimuth with it.
- **Shape of hits per particle against eta**: both are flat at 5 to 6 in the
  barrel and peak at |eta| ~ 3, the fast simulation just sits uniformly at 62% of
  the full one.

Not so good, in rough order of how much it matters:

- **The eta distribution is too forward.** The generator is flat in eta by
  construction; the real minimum-bias distribution falls off beyond |eta| ~ 2, so
  the ratio rises from 1.0 in the barrel to 1.8 at |eta| = 4. A falling eta
  density would be a cheap improvement.
- **Hits per particle are 36% low**, uniformly in eta. The layout simply has fewer
  surfaces than the real ITk: five barrel cylinders and nine disks per side give
  at most fourteen crossings, and the real detector's overlaps and ring sections
  give more.
- **The d0 distribution is far too narrow.** `d0Sigma = 0.1 mm` produces a tight
  spike where the full simulation has a broad distribution reaching past 2 mm.
  The comment on that parameter claims it is "widened to stand in for the tail of
  tracks from heavy-flavour and strange decays"; the data says it is not widened
  nearly enough, and that a single Gaussian is the wrong shape for it.
- **The primary/secondary split is wrong even though the total is right.** The
  generator makes 5.75 times too many secondaries, each with fewer hits, which
  happens to land the total space point count in the right place. Part of this is
  a genuine difference in bookkeeping rather than in physics: only about half of
  the real pixel clusters carry a truth link at all, while every synthetic space
  point belongs to a particle. So the real "unlinked" component has no counterpart
  in the fast simulation, and the surplus secondaries stand in for it. That is
  what `secondaryRate` is documented to absorb, but it means the secondary
  distributions are not a like-for-like comparison.

## The ITk endcap is not disks

The `z` distribution disagrees visibly: the fast simulation piles its endcap hits
onto nine discrete disk positions while the full simulation is much flatter. This
is not a mistuning, it is the layout model.

Grouping the dump's pixel clusters by `CLlayer_disk` shows that each endcap group
is a **ring at roughly fixed radius spanning a long range in z**, not a planar
disk at fixed z. For example group 0 sits at r = 33 to 53 mm across |z| from
261 mm outwards, which is geometrically a cylinder. That is the ITk's inclined and
ring structure, and the synthetic model has no way to express it: its endcap
surfaces are planar disks.

The barrel, by contrast, comes out almost exactly as the layout has it:

| | dump | `itkPixelDescription()` |
| --- | --- | --- |
| barrel radii [mm] | 34.3, 99.4, 160.3, 228.2, 291.1 | 34, 99, 160, 228, 291 |

So the nine disks are a stand-in for the endcap rather than a description of it.
Since ACTS has no ITk geometry, this is also the only way to check those numbers
at all - the ODD and Generic layouts are checked against their built geometry in
`Python/Examples/tests/test_fatras_synthetic_layout.py`, and the ITk one cannot
be.

## Still to do

The ODD comparison against ColliderML, which needs `openDataDetectorTtbarConfig()`
to be fitted: the ODD pixel detector ends at r = 200 mm and |z| = 1.5 m against
the ITk's 320 mm and 2.8 m, so `materialRScale` and `materialZScale` in particular
cannot carry over.
