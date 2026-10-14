#!/usr/bin/env python3
"""Use the shared ODD validation plotter, including explicit map comparisons."""

from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(
        str(
            Path(__file__).resolve().parent.parent
            / "fatras-neutral-hadrons/odd/compare.py"
        ),
        run_name="__main__",
    )
