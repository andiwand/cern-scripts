"""Two-panel summary figure for acts#6211.

    uv run --with numpy --with matplotlib money.py MERGED_DIR OUT_STEM

Left: trajectory error against wall time, analytic field, 1 GeV, 10 m.
Right: jacobian error against path length, with and without dB/dr.
Writes OUT_STEM-light.png, OUT_STEM-dark.png and OUT_STEM.pdf (light).
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/rk-validation-mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms
import numpy as np

MERGED = Path(sys.argv[1])
STEM = Path(sys.argv[2])

rows = defaultdict(list)
with (MERGED / "all.jsonl").open() as f:
    for line in f:
        r = json.loads(line)
        if r.get("ok", True):
            rows[r["study"]].append(r)


def is_1gev(r):
    return abs(r["p"] - 1.0) < 1e-9


def median_by(sel, key, value):
    groups = defaultdict(list)
    for r in sel:
        groups[key(r)].append(value(r))
    return {k: float(np.median(v)) for k, v in groups.items()}


# Left: |dr| at 10 m (median of 8 directions) against wall time
err = median_by(
    [r for r in rows["inh"] if is_1gev(r) and abs(r["s"] - 1e4) < 1e-3],
    lambda r: (r["stepper"], r["tol"]),
    lambda r: r["dpos"],
)
left = {}
for st in ["sympy", "dp5", "vern9"]:
    left[st] = sorted(
        (r["us"], err[(st, r["tol"])])
        for r in rows["time"]
        if r["stepper"] == st and is_1gev(r) and r.get("us") is not None and (st, r["tol"]) in err
    )

# Right: best jacobian error over the tolerances, max of the column groups
right = {}
for st in ["sympy", "vern9", "vern9-nograd"]:
    med = median_by(
        [r for r in rows["jac"] if r["stepper"] == st and is_1gev(r)],
        lambda r: (r["s"], r["tol"]),
        lambda r: max(r["jac"]),
    )
    best = {}
    for (s, _), e in med.items():
        best[s] = min(best.get(s, np.inf), e)
    right[st] = sorted(best.items())
fd = sorted(
    median_by(
        [r for r in rows["jacfd"] if is_1gev(r)], lambda r: r["s"], lambda r: max(r["jac"])
    ).items()
)

COLORS = {
    "light": {"sympy": "#2a78d6", "dp5": "#eda100", "vern9": "#e87ba4"},
    "dark": {"sympy": "#3987e5", "dp5": "#c98500", "vern9": "#d55181"},
}
THEME = {
    "light": dict(bg="#fbfcfd", fg="#14181f", muted="#5b6472", grid="#d9dee5", ref="#8a93a0"),
    "dark": dict(bg="#151a21", fg="#e8ebef", muted="#a3acb8", grid="#2c343f", ref="#7d8794"),
}


def lookup(curve, target):
    """Wall time to reach target, interpolated in log-log."""
    for (t0, e0), (t1, e1) in zip(curve, curve[1:]):
        if e0 > target >= e1:
            f = (np.log(target) - np.log(e0)) / (np.log(e1) - np.log(e0))
            return float(np.exp(np.log(t0) + f * (np.log(t1) - np.log(t0))))
    return None


def draw(theme):
    t = THEME[theme]
    c = COLORS[theme]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.facecolor": t["bg"],
            "figure.facecolor": t["bg"],
            "savefig.facecolor": t["bg"],
            "axes.edgecolor": t["muted"],
            "axes.labelcolor": t["fg"],
            "xtick.color": t["muted"],
            "ytick.color": t["muted"],
            "text.color": t["fg"],
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.color": t["grid"],
            "grid.linewidth": 0.6,
            "lines.linewidth": 1.8,
            "pdf.fonttype": 42,
        }
    )
    fig, (a, b) = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax in (a, b):
        ax.grid(True)
        ax.set_axisbelow(True)
        ax.set_xscale("log")
        ax.set_yscale("log")

    # Left panel
    names = {"sympy": "SympyStepper", "dp5": "Runge-Kutta DP5(4)", "vern9": "Runge-Kutta Verner 9(8)"}
    marks = {"sympy": "o", "dp5": "D", "vern9": "v"}
    # Direct labels next to one point of each curve, clear of the others
    place = {"sympy": (1e-4, (8, 4), "left"), "dp5": (1e-5, (8, 2), "left"), "vern9": (3e-9, (8, 0), "left")}
    for st, pts in left.items():
        a.plot([p[0] for p in pts], [max(p[1], 1e-12) for p in pts], color=c[st], marker=marks[st], ms=4)
        target, off, ha = place[st]
        if st == "vern9":
            # Below the plateau, where no other curve runs
            anchor, off, va = min(pts, key=lambda p: p[1]), (0, -10), "top"
        else:
            anchor, va = (lookup(pts, target), target), "bottom"
        a.annotate(names[st], anchor, xytext=off, textcoords="offset points",
                   color=t["fg"], fontsize=9, ha=ha, va=va)
    tr = matplotlib.transforms.blended_transform_factory(a.transAxes, a.transData)
    lines = []
    for target, label in [(1e-6, "1 nm"), (1e-9, "1 pm")]:
        ts, tv = lookup(left["sympy"], target), lookup(left["vern9"], target)
        a.axhline(target, color=t["ref"], lw=0.8, ls=":")
        a.text(0.01, target * 1.4, label, transform=tr, ha="left", va="bottom", color=t["muted"], fontsize=8.5)
        if ts and tv:
            lines.append(f"{label}: Verner {tv:.0f} µs, Sympy {ts:.0f} µs")
    a.text(0.98, 0.97, "\n".join(lines), transform=a.transAxes, ha="right", va="top",
           color=t["fg"], fontsize=9, linespacing=1.5)
    a.set_ylim(bottom=5e-12)
    a.set_xlabel("wall time per track [µs], no covariance")
    a.set_ylabel("|Δr| to reference at 10 m [mm]")
    a.set_title("Trajectory: accuracy for the cost", loc="left", fontweight="bold", fontsize=11)

    # Right panel
    s_with = right["vern9"]
    s_without = right["vern9-nograd"]
    s_sympy = right["sympy"]
    b.plot([p[0] / 1000 for p in s_with], [p[1] for p in s_with], color=c["vern9"], marker="v", ms=4)
    b.plot([p[0] / 1000 for p in s_without], [p[1] for p in s_without], color=c["vern9"], marker="v", ms=5, mfc="none", ls="--")
    b.plot([p[0] / 1000 for p in s_sympy], [p[1] for p in s_sympy], color=c["sympy"], marker="o", ms=3, lw=1.2)
    b.plot([p[0] / 1000 for p in fd], [p[1] for p in fd], color=t["ref"], ls=":", lw=1.2)
    b.annotate("Runge-Kutta with dB/dr", (s_with[3][0] / 1000, s_with[3][1]), xytext=(0, -10), textcoords="offset points", color=t["fg"], fontsize=9, va="top")
    b.annotate("SympyStepper, and\nRunge-Kutta without dB/dr", (s_sympy[2][0] / 1000, s_sympy[2][1]), xytext=(6, 2), textcoords="offset points", color=t["fg"], fontsize=9)
    b.annotate("finite-difference precision", (fd[-3][0] / 1000, fd[-3][1]), xytext=(-40, 8), textcoords="offset points", color=t["muted"], fontsize=8.5)
    b.set_ylim(bottom=1.5e-11)
    b.set_xlabel("path length [m]")
    b.set_ylabel("relative error of the transport jacobian")
    b.set_title("Jacobian: only correct with dB/dr", loc="left", fontweight="bold", fontsize=11)

    fig.text(
        0.01,
        0.01,
        "1 GeV pion, smooth inhomogeneous field (2 T, 30 % modulation over 1.5 m), vacuum. Median of 8 directions. "
        "Reference: Verner, fixed 2 mm step; jacobian: Richardson central differences.",
        color=t["muted"],
        fontsize=8,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    return fig


for theme in ("light", "dark"):
    fig = draw(theme)
    fig.savefig(f"{STEM}-{theme}.png", dpi=170)
    if theme == "light":
        fig.savefig(f"{STEM}.pdf")
    plt.close(fig)
print("written", STEM)
