# GX2F energy loss validation

Standalone harnesses and analysis for the GX2F energy loss validation.
The note is `cern-notes/acts/notebook/2026-10-10_gx2f-energy-loss-validation.md`. The data, logs, plots and `index.html` stay in the companion folder of that note.

The Python scripts read and write `~/cern/notes/acts/notebook/2026-10-10_gx2f-energy-loss-validation`. Run the harnesses from that folder.

## Scripts

- `build_validation.py --build B [--source S]`: compiles a harness against an ACTS build with the GX2F entry of its `compile_commands.json`. The binary lands next to the source.
- `validation.cpp`: the track harness. `matrix_validation.cpp`: the matrix harness.
- `analyze.py`: `tracks.csv(.gz)` to `summary.json` and `summary.csv`.
- `plot.py`: the PDF and PNG figures in `plots/`.
- `make_report.py`: `index.html`.
- `check_report.py`: browser check of `index.html` with Playwright.
- `requirements.txt`: the pinned Python dependencies.
