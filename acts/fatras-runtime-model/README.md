# Compact Fatras runtime model — dependency review

WP1 is the first blocker: remove the mandatory custom hadronic event library.
This package currently contains only a streaming byte-accounting tool. No new
physics generator or calibration is implemented.

```sh
python3 audit-library.py /path/to/silicon-all-low.table \
  --output results/2026-10-15/library-byte-audit.json
```

The V1 audit hashes every byte and accounts separately for rate/node headers,
event target/remnant records and daughters without loading the event catalogue.
It checks format/termination and total byte accounting; it is not a substitute
for the ACTS physics/conservation validator. The recorded table has 771 nodes,
386304 events and 6364029 daughters. Rates/indexing use about 32 KiB; event records
use 99.994% of the 561 MiB. Algorithmic final states are the main replacement task.
The large file remains in the existing external validation package.
