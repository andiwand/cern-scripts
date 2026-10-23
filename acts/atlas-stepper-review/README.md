# Atlas stepper review

Report generator for the Atlas stepper review.
The note is `cern-notes/acts/notebook/2026-10-12_atlas-stepper-review.md`.

`make_report.py` reads `cpu-results.json` in `~/cern/notes/acts/notebook/2026-10-12_atlas-stepper-review` and writes the Markdown note, the standalone HTML and `plots/cpu-comparison.pdf`.
Regenerating rewrites the PDF, and the standalone HTML embeds it, so both change in git even when the data is the same.

## Scripts

- `make_report.py`: the Markdown note, the HTML and the PDF.
- `check_report.py`: browser check of the standalone HTML with Playwright.
