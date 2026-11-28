# RZ track finder vs CKF

Runs the CKF or the RZ finder on the same simulated events (generic detector,
`--odd`, or `--itk` from `~/cern/source/acts/acts-itk`) and compares them.
Needs an ACTS build with the RZ finder. Notes: `acts/notebook/2026-09-*_rz-*`
in the notes repo.

- `compare.py --finder ckf|rz --out DIR [...]`: the chain with the usual
  performance and track writers. `--ttbar --pileup N` for Pythia8, RZ knobs
  `--max-holes`, `--window-sigmas`, `--material-tables`, `--batch`, ...
- `summarize.py DIR...`: efficiency, fake/duplicate ratios, hits per track,
  perigee pulls and time per event side by side.
- `robust.py DIR...`: robust (MAD) pull widths, pull tails and d0/z0
  resolutions from `tracksummary_{ckf,rz}.root`.
- `pmc.py TAG`: CPU counters (cycles, instructions, stalls, flushes) inside
  the finder's signposts, from an Instruments trace exported as
  `TAG-signpost.xml` and `TAG-counters.xml`.

```sh
out=~/cern/data/rz-track-finder
python compare.py --finder ckf --out $out/muon-ckf
python compare.py --finder rz --out $out/muon-rz
python summarize.py $out/muon-ckf $out/muon-rz

# CPU counters of the RZ finder on ITk ttbar PU200
xctrace record --template 'CPU Counters' --instrument 'Points of Interest' \
  --output $out/t.trace --launch -- $(which python) compare.py --finder rz \
  --itk --ttbar --pileup 200 --out $out/t --events 5
xctrace export --input $out/t.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="os-signpost"]' > $out/t-signpost.xml
xctrace export --input $out/t.trace \
  --xpath '/trace-toc/run[@number="1"]/data/table[@schema="kdebug-counters-with-time-sample"]' > $out/t-counters.xml
python pmc.py $out/t
```
