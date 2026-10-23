"""Plots for the Runge-Kutta stepper validation.

    uv run --with numpy --with matplotlib plot.py DATA_DIR OUT_DIR

DATA_DIR holds the JSON lines of `validate <study>` as <study>.jsonl.
OUT_DIR receives one PNG per figure and theme, and summary.json with the
numbers that the report quotes.
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
import numpy as np

DATA = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

STEPPERS = ["sympy", "helix", "rk4", "dp5", "vern9"]
LABEL = {
    "sympy": "SympyStepper",
    "helix": "HelixStepper, patched",
    "rk4": "RK4, step doubling",
    "dp5": "DP5(4), embedded",
    "vern9": "Verner 9(8), embedded",
    "dp5-nograd": "DP5(4), no dB/dr",
    "vern9-nograd": "Verner 9(8), no dB/dr",
}
MARK = {"sympy": "o", "helix": "s", "rk4": "^", "dp5": "D", "vern9": "v"}
# Categorical slots 1-5 of the reference palette, light and dark steps
COLORS = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"],
}
THEME = {
    "light": dict(bg="#fbfcfd", fg="#14181f", muted="#5b6472", grid="#d9dee5", ref="#8a93a0"),
    "dark": dict(bg="#151a21", fg="#e8ebef", muted="#a3acb8", grid="#2c343f", ref="#7d8794"),
}
PCOL = {0.1: "0.1 GeV", 1.0: "1 GeV", 10.0: "10 GeV"}


def color(name, theme):
    base = name.replace("-nograd", "")
    return COLORS[theme][STEPPERS.index(base)]


def style(name):
    base = name.replace("-nograd", "")
    return dict(
        marker=MARK[base],
        ls="--" if name.endswith("nograd") else "-",
        mfc="none" if name.endswith("nograd") else None,
    )


_rows = defaultdict(list)
for path in sorted(DATA.glob("*.jsonl")):
    with path.open() as f:
        for line in f:
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue  # a run that was cut off
            if r.get("ok", True):
                _rows[r["study"]].append(r)


def load(study):
    return _rows.get(study, [])


def pkey(p):
    return round(p, 3)


def median_by(rows, keys, value):
    groups = defaultdict(list)
    for r in rows:
        v = value(r)
        if v is None:
            continue
        groups[tuple(r[k] if k != "p" else pkey(r[k]) for k in keys)].append(v)
    return {k: float(np.median(v)) for k, v in groups.items()}


def floor(v, lo=1e-17):
    return max(v, lo)


def fmt_s(s):
    return f"{s / 1000:g} m" if s >= 1000 else f"{s / 10:g} cm"


summary = {}


def figure(name, nrows, ncols, draw, width=11.0, height=3.4, title=None, sharey=True):
    for theme in ("light", "dark"):
        t = THEME[theme]
        plt.rcParams.update(
            {
                "font.family": "DejaVu Sans",
                "font.size": 9.5,
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
                "lines.linewidth": 1.6,
                "lines.markersize": 5,
                "legend.frameon": False,
            }
        )
        fig, axes = plt.subplots(
            nrows, ncols, figsize=(width, height * nrows), squeeze=False, sharey=sharey
        )
        for ax in axes.flat:
            ax.grid(True, which="major")
            ax.set_axisbelow(True)
        draw(fig, axes, theme, t)
        if title:
            fig.suptitle(title, x=0.01, ha="left", fontsize=11, fontweight="bold")
        # Space at the bottom for a figure legend, in inches
        legend_in = getattr(fig, "legend_in", 0.0)
        fig.tight_layout(rect=(0, legend_in / fig.get_figheight(), 1, 1))
        fig.savefig(OUT / f"{name}-{theme}.png", dpi=150)
        plt.close(fig)


def legend_below(fig, axes, names, theme):
    handles = [
        plt.Line2D([], [], color=color(n, theme), label=LABEL[n], **style(n)) for n in names
    ]
    fig.legend(handles=handles, loc="lower center", ncol=len(names), bbox_to_anchor=(0.5, -0.01))
    fig.legend_in = 0.45


# ---------------------------------------------------------------------------
# Work-precision helpers


def wp_curves(rows, s, p, cost_key="lookups"):
    """stepper -> sorted list of (median cost, median dpos, tol)."""
    sel = [r for r in rows if abs(r["s"] - s) < 1e-6 * s and pkey(r["p"]) == p]
    err = median_by(sel, ["stepper", "tol"], lambda r: r["dpos"])
    cost = median_by(sel, ["stepper", "tol"], lambda r: r[cost_key])
    out = defaultdict(list)
    for (st, tol), e in err.items():
        out[st].append((cost[(st, tol)], e, tol))
    return {k: sorted(v) for k, v in out.items()}


def best_vs_s(rows, p, stepper):
    sel = [r for r in rows if r["stepper"] == stepper and pkey(r["p"]) == p]
    med = median_by(sel, ["s", "tol"], lambda r: r["dpos"])
    best = defaultdict(lambda: (np.inf, None))
    for (s, tol), e in med.items():
        if e < best[s][0]:
            best[s] = (e, tol)
    return sorted((s, e, tol) for s, (e, tol) in best.items())


def cost_for_target(curve, target):
    """Interpolate the lookups needed to reach target, on the lower envelope."""
    pts = sorted(curve)
    best = np.inf
    for (c0, e0, _), (c1, e1, _) in zip(pts, pts[1:]):
        if e0 <= target:
            best = min(best, c0)
        if (e0 - target) * (e1 - target) < 0 and e0 > 0 and e1 > 0:
            f = (np.log(target) - np.log(e0)) / (np.log(e1) - np.log(e0))
            best = min(best, float(np.exp(np.log(c0) + f * (np.log(c1) - np.log(c0)))))
    if pts and pts[-1][1] <= target:
        best = min(best, pts[-1][0])
    return best if np.isfinite(best) else None


# ---------------------------------------------------------------------------
# 1. Homogeneous field

hom = [r for r in load("hom") if not r["jacrun"]]
homjac = [r for r in load("hom") if r["jacrun"]]
homfd = load("homfd")
moms = [0.1, 1.0, 10.0]
scanned = ["sympy", "rk4", "dp5", "vern9"]

if hom:

    def draw(fig, axes, theme, t):
        for ax, p in zip(axes[0], moms):
            for st in scanned + ["helix"]:
                pts = best_vs_s(hom, p, st)
                if not pts:
                    continue
                ax.plot(
                    [x[0] / 1000 for x in pts],
                    [floor(x[1]) for x in pts],
                    color=color(st, theme),
                    **style(st),
                )
            s = np.logspace(-2, 2, 50)
            ax.plot(s, 1.1e-16 * s * 1000, color=t["ref"], lw=1, ls=":")
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"p = {PCOL[p]}", loc="left", fontsize=10)
            ax.set_xlabel("path length [m]")
        axes[0][0].set_ylabel("best |Δr| to the analytic helix [mm]")
        axes[0][0].text(0.012, 1.1e-16 * 12 * 1.8, "ε·s", color=t["ref"], fontsize=8)
        legend_below(fig, axes, scanned + ["helix"], theme)

    figure("hom-best", 1, 3, draw)

    summary["hom_best"] = {
        f"{st}@{p}": [[s, e, tol] for s, e, tol in best_vs_s(hom, p, st)]
        for st in scanned + ["helix"]
        for p in moms
    }

    def draw(fig, axes, theme, t):
        for i, p in enumerate(moms):
            for j, s in enumerate([1000.0, 10000.0, 100000.0]):
                ax = axes[i][j]
                curves = wp_curves(hom, s, p)
                for st in scanned:
                    if st not in curves:
                        continue
                    c = curves[st]
                    ax.plot(
                        [x[0] for x in c],
                        [floor(x[1]) for x in c],
                        color=color(st, theme),
                        **style(st),
                        ms=3.5,
                    )
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_title(f"{PCOL[p]}, s = {fmt_s(s)}", loc="left", fontsize=10)
                if i == 2:
                    ax.set_xlabel("field lookups per track")
            axes[i][0].set_ylabel("|Δr| [mm]")
        legend_below(fig, axes, scanned, theme)

    figure("hom-wp", 3, 3, draw, height=3.0, sharey=False)

if homjac:
    groups = ["loc0, loc1", "φ, θ", "q/p"]

    def draw(fig, axes, theme, t):
        for row, mode in enumerate(["best", "default"]):
            for g in range(3):
                ax = axes[row][g]
                for st in scanned + ["helix"]:
                    sel = [r for r in homjac if r["stepper"] == st and pkey(r["p"]) == 1.0]
                    if mode == "default" and st != "helix":
                        sel = [r for r in sel if abs(r["tol"] - 1e-4) < 1e-12]
                    med = median_by(sel, ["s", "tol"], lambda r: r["jac"][g])
                    best = {}
                    for (s, tol), e in med.items():
                        best[s] = min(best.get(s, np.inf), e)
                    pts = sorted(best.items())
                    ax.plot(
                        [x[0] / 1000 for x in pts],
                        [floor(x[1]) for x in pts],
                        color=color(st, theme),
                        **style(st),
                    )
                fd = median_by(
                    [r for r in homfd if pkey(r["p"]) == 1.0], ["s"], lambda r: r["jac"][g]
                )
                pts = sorted(fd.items())
                ax.plot(
                    [x[0][0] / 1000 for x in pts],
                    [floor(x[1]) for x in pts],
                    color=t["ref"],
                    ls=":",
                    lw=1.2,
                )
                ax.set_xscale("log")
                ax.set_yscale("log")
                what = "best tolerance" if mode == "best" else "tolerance 1e-4"
                ax.set_title(f"columns {groups[g]}, {what}", loc="left", fontsize=10)
                if row == 1:
                    ax.set_xlabel("path length [m]")
            axes[row][0].set_ylabel("relative jacobian error")
        legend_below(fig, axes, scanned + ["helix"], theme)

    figure("hom-jac", 2, 3, draw, height=3.1)

# ---------------------------------------------------------------------------
# 2. Inhomogeneous field and field map


def ref_band(refrows, p):
    med = median_by([r for r in refrows if pkey(r["p"]) == p], ["s"], lambda r: r["dpos"])
    return sorted((k[0], v) for k, v in med.items())


for study, paths, title in [
    ("inh", [1000.0, 10000.0, 100000.0], "analytic field"),
    ("map", [100.0, 1000.0, 10000.0], "field map"),
    ("mapcap", [100.0, 1000.0, 10000.0], "field map, step ≤ 20 mm"),
]:
    rows = load(study)
    refrows = load(study + "ref")
    if not rows:
        continue
    steppers = STEPPERS

    def draw(fig, axes, theme, t, rows=rows, refrows=refrows, paths=paths):
        for i, p in enumerate(moms):
            band = dict(ref_band(refrows, p))
            for j, s in enumerate(paths):
                ax = axes[i][j]
                curves = wp_curves(rows, s, p)
                for st in steppers:
                    if st not in curves:
                        continue
                    c = curves[st]
                    ax.plot(
                        [x[0] for x in c],
                        [floor(x[1]) for x in c],
                        color=color(st, theme),
                        **style(st),
                        ms=3.5,
                    )
                if s in band:
                    ax.axhline(floor(band[s]), color=t["ref"], ls=":", lw=1.2)
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_title(f"{PCOL[p]}, s = {fmt_s(s)}", loc="left", fontsize=10)
                if i == 2:
                    ax.set_xlabel("field lookups per track")
            axes[i][0].set_ylabel("|Δr| to reference [mm]")
        legend_below(fig, axes, steppers, theme)

    figure(f"{study}-wp", 3, 3, draw, height=3.0, sharey=False)

    def draw(fig, axes, theme, t, rows=rows, refrows=refrows):
        for ax, p in zip(axes[0], moms):
            for st in steppers:
                pts = best_vs_s(rows, p, st)
                ax.plot(
                    [x[0] / 1000 for x in pts],
                    [floor(x[1]) for x in pts],
                    color=color(st, theme),
                    **style(st),
                )
            band = ref_band(refrows, p)
            ax.plot(
                [x[0] / 1000 for x in band],
                [floor(x[1]) for x in band],
                color=t["ref"],
                ls=":",
                lw=1.2,
            )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"p = {PCOL[p]}", loc="left", fontsize=10)
            ax.set_xlabel("path length [m]")
        axes[0][0].set_ylabel("best |Δr| to reference [mm]")
        legend_below(fig, axes, steppers, theme)

    figure(f"{study}-best", 1, 3, draw)

    summary[f"{study}_best"] = {
        f"{st}@{p}": [[s, e, tol] for s, e, tol in best_vs_s(rows, p, st)]
        for st in steppers
        for p in moms
    }
    summary[f"{study}_ref"] = {str(p): ref_band(refrows, p) for p in moms}

# ---------------------------------------------------------------------------
# 3. Forward-backward

fb = load("fb")
inh = load("inh")
if fb:

    def draw(fig, axes, theme, t):
        for ax, p in zip(axes[0], moms):
            for st in STEPPERS:
                sel = [
                    r
                    for r in fb
                    if r["stepper"] == st and pkey(r["p"]) == p and abs(r["tol"] - 1e-4) < 1e-12
                ]
                med = sorted(median_by(sel, ["s"], lambda r: r["dpos"]).items())
                ax.plot(
                    [x[0][0] / 1000 for x in med],
                    [floor(x[1]) for x in med],
                    color=color(st, theme),
                    **style(st),
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"p = {PCOL[p]}, tolerance 1e-4", loc="left", fontsize=10)
            ax.set_xlabel("path length [m]")
        axes[0][0].set_ylabel("closure |Δr| after s forward, s back [mm]")
        legend_below(fig, axes, STEPPERS, theme)

    figure("fb-default", 1, 3, draw)

    # Closure against the true one-way error, same stepper, tolerance, path
    truth = {
        (r["stepper"], pkey(r["p"]), r["dir"], r["tol"], r["s"]): r["dpos"] for r in inh
    }
    pairs = defaultdict(list)
    for r in fb:
        k = (r["stepper"], pkey(r["p"]), r["dir"], r["tol"], r["s"])
        if k in truth:
            pairs[r["stepper"]].append((truth[k], r["dpos"]))

    def draw(fig, axes, theme, t):
        for ax, st in zip(axes[0], STEPPERS):
            xy = np.array(pairs[st]) if pairs[st] else np.zeros((0, 2))
            if len(xy):
                ax.scatter(
                    np.maximum(xy[:, 0], 1e-17),
                    np.maximum(xy[:, 1], 1e-17),
                    s=4,
                    color=color(st, theme),
                    alpha=0.35,
                    marker=MARK[st],
                    linewidths=0,
                )
            lim = (1e-15, 1e5)
            ax.plot(lim, lim, color=t["ref"], lw=1, ls=":")
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(LABEL[st], loc="left", fontsize=10)
            ax.set_xlabel("one-way |Δr| to reference [mm]")
        axes[0][0].set_ylabel("forward-backward closure [mm]")

    figure("fb-vs-truth", 1, 5, draw, width=13.5, height=3.2)

    under = {}
    for st, xy in pairs.items():
        if not xy:
            continue
        xy = np.array(xy)
        sel = xy[:, 0] > 1e-9
        under[st] = {
            "n": int(sel.sum()),
            "median_ratio": float(np.median(xy[sel, 1] / xy[sel, 0])) if sel.any() else None,
            "frac_closure_below_tenth": float(np.mean(xy[sel, 1] < 0.1 * xy[sel, 0]))
            if sel.any()
            else None,
        }
    summary["fb_vs_truth"] = under

# ---------------------------------------------------------------------------
# 4. Jacobian in the analytic field

jac = load("jac")
jacfd = load("jacfd")
if jac:
    names = STEPPERS + ["dp5-nograd", "vern9-nograd"]
    groups = ["loc0, loc1", "φ, θ", "q/p"]

    def jac_best(p, st, g):
        sel = [r for r in jac if r["stepper"] == st and pkey(r["p"]) == p]
        med = median_by(sel, ["s", "tol"], lambda r: r["jac"][g])
        best = {}
        for (s, tol), e in med.items():
            best[s] = min(best.get(s, np.inf), e)
        return sorted(best.items())

    def draw(fig, axes, theme, t):
        for i, p in enumerate(moms):
            for g in range(3):
                ax = axes[i][g]
                for st in names:
                    pts = jac_best(p, st, g)
                    ax.plot(
                        [x[0] / 1000 for x in pts],
                        [floor(x[1]) for x in pts],
                        color=color(st, theme),
                        **style(st),
                        ms=4,
                    )
                fd = sorted(
                    median_by(
                        [r for r in jacfd if pkey(r["p"]) == p], ["s"], lambda r: r["jac"][g]
                    ).items()
                )
                ax.plot(
                    [x[0][0] / 1000 for x in fd],
                    [floor(x[1]) for x in fd],
                    color=t["ref"],
                    ls=":",
                    lw=1.2,
                )
                ax.set_xscale("log")
                ax.set_yscale("log")
                ax.set_title(f"{PCOL[p]}, columns {groups[g]}", loc="left", fontsize=10)
                if i == 2:
                    ax.set_xlabel("path length [m]")
            axes[i][0].set_ylabel("best relative error")
        handles = [
            plt.Line2D([], [], color=color(n, theme), label=LABEL[n], **style(n)) for n in names
        ]
        fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.005))
        fig.legend_in = 0.7

    figure("jac-best", 3, 3, draw, height=3.0)

    summary["jac_best"] = {
        f"{st}@{p}@{g}": jac_best(p, st, g) for st in names for p in moms for g in range(3)
    }

    # Error against cost at 1 m and 10 m, 1 GeV, all column groups (max)
    def draw(fig, axes, theme, t):
        for ax, s in zip(axes[0], [1000.0, 10000.0, 100000.0]):
            for st in names:
                sel = [
                    r
                    for r in jac
                    if r["stepper"] == st and pkey(r["p"]) == 1.0 and abs(r["s"] - s) < 1e-6 * s
                ]
                err = median_by(sel, ["tol"], lambda r: max(r["jac"]))
                cost = median_by(sel, ["tol"], lambda r: r["lookups"])
                pts = sorted((cost[k], v) for k, v in err.items())
                ax.plot(
                    [x[0] for x in pts],
                    [floor(x[1]) for x in pts],
                    color=color(st, theme),
                    **style(st),
                    ms=3.5,
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"1 GeV, s = {fmt_s(s)}", loc="left", fontsize=10)
            ax.set_xlabel("field lookups per track, with jacobian")
        axes[0][0].set_ylabel("max relative jacobian error")
        handles = [
            plt.Line2D([], [], color=color(n, theme), label=LABEL[n], **style(n)) for n in names
        ]
        fig.legend(handles=handles, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
        fig.legend_in = 0.7

    figure("jac-wp", 1, 3, draw, height=3.6, sharey=False)

# ---------------------------------------------------------------------------
# 5. Cost at a fixed accuracy, and time

if inh:
    targets = [1e-3, 1e-6]
    paths_all = sorted({r["s"] for r in inh})
    cost_table = {}

    def draw(fig, axes, theme, t):
        for i, target in enumerate(targets):
            for j, p in enumerate(moms):
                ax = axes[i][j]
                for st in STEPPERS:
                    xs, ys = [], []
                    for s in paths_all:
                        c = wp_curves(inh, s, p).get(st)
                        v = cost_for_target(c, target) if c else None
                        cost_table[f"{st}@{p}@{target}@{s}"] = v
                        if v is not None:
                            xs.append(s / 1000)
                            ys.append(v)
                    ax.plot(xs, ys, color=color(st, theme), **style(st))
                ax.set_xscale("log")
                ax.set_yscale("log")
                tl = "1 µm" if target == 1e-3 else "1 nm"
                ax.set_title(f"{PCOL[p]}, |Δr| ≤ {tl}", loc="left", fontsize=10)
                if i == 1:
                    ax.set_xlabel("path length [m]")
            axes[i][0].set_ylabel("field lookups per track")
        legend_below(fig, axes, STEPPERS, theme)

    figure("cost", 2, 3, draw, height=3.1)
    summary["cost"] = cost_table

timing = load("time")
if timing and inh:
    def draw(fig, axes, theme, t):
        for ax, p in zip(axes[0], moms):
            err = median_by(
                [r for r in inh if pkey(r["p"]) == p and abs(r["s"] - 10000.0) < 1e-3],
                ["stepper", "tol"],
                lambda r: r["dpos"],
            )
            for st in STEPPERS:
                pts = sorted(
                    (r["us"], err[(st, r["tol"])])
                    for r in timing
                    if r["stepper"] == st
                    and pkey(r["p"]) == p
                    and r.get("us") is not None
                    and (st, r["tol"]) in err
                )
                ax.plot(
                    [x[0] for x in pts],
                    [floor(x[1]) for x in pts],
                    color=color(st, theme),
                    **style(st),
                    ms=3.5,
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"{PCOL[p]}, s = 10 m", loc="left", fontsize=10)
            ax.set_xlabel("wall time per track [µs]")
        axes[0][0].set_ylabel("|Δr| to reference [mm]")
        legend_below(fig, axes, STEPPERS, theme)

    figure("time", 1, 3, draw, sharey=False)
    summary["time"] = [r for r in timing]

timecov = load("timecov")
if timecov and jac:
    jerr = median_by(
        [r for r in jac if pkey(r["p"]) == 1.0 and abs(r["s"] - 10000.0) < 1e-3],
        ["stepper", "tol"],
        lambda r: max(r["jac"]),
    )
    perr = median_by(
        [r for r in inh if pkey(r["p"]) == 1.0 and abs(r["s"] - 10000.0) < 1e-3],
        ["stepper", "tol"],
        lambda r: r["dpos"],
    )

    def draw(fig, axes, theme, t):
        for ax, (err, what) in zip(axes[0], [(perr, "|Δr| to reference [mm]"), (jerr, "max relative jacobian error")]):
            for st in STEPPERS:
                pts = sorted(
                    (r["us"], err[(st, r["tol"])])
                    for r in timecov
                    if r["stepper"] == st and r.get("us") is not None and (st, r["tol"]) in err
                )
                ax.plot([x[0] for x in pts], [floor(x[1]) for x in pts], color=color(st, theme), **style(st), ms=3.5)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_ylabel(what)
            ax.set_xlabel("wall time per track with covariance [µs]")
        axes[0][0].set_title("1 GeV, s = 10 m, trajectory", loc="left", fontsize=10)
        axes[0][1].set_title("1 GeV, s = 10 m, jacobian", loc="left", fontsize=10)
        legend_below(fig, axes, STEPPERS, theme)

    figure("timecov", 1, 2, draw, width=11.0, height=3.6, sharey=False)
    summary["timecov"] = timecov

# ---------------------------------------------------------------------------
# 6. Step-size profile

prof = load("prof")
if prof:

    def draw(fig, axes, theme, t):
        for i, p in enumerate([0.5, 2.0]):
            for j, tol in enumerate([1e-4, 1e-8]):
                ax = axes[i][j]
                for st in STEPPERS:
                    r = next(
                        (
                            r
                            for r in prof
                            if r["stepper"] == st
                            and abs(r["p"] - p) < 1e-9
                            and abs(r["tol"] - tol) < 1e-15
                        ),
                        None,
                    )
                    if r is None or not r["steps"]:
                        continue
                    a = np.array(r["steps"])
                    ax.step(
                        a[:, 0] / 1000,
                        np.abs(a[:, 1]),
                        where="pre",
                        color=color(st, theme),
                        lw=1.2,
                        label=f"{LABEL[st]} ({len(a)} steps)",
                    )
                ax.set_yscale("log")
                ax.set_title(f"p = {p:g} GeV, tolerance {tol:g}", loc="left", fontsize=10)
                ax.legend(fontsize=7.5, loc="lower right", ncol=2)
                if i == 1:
                    ax.set_xlabel("path length [m]")
            axes[i][0].set_ylabel("step size [mm]")

    figure("prof", 2, 2, draw, height=3.2, sharey=False)

# ---------------------------------------------------------------------------
# 7. Tolerance scans at a fixed distance, and steps as the cost


def tol_scan(rows, steppers, s, name, what):
    def draw(fig, axes, theme, t):
        for j, p in enumerate(moms):
            sel = [r for r in rows if abs(r["s"] - s) < 1e-6 * s and pkey(r["p"]) == p]
            err = median_by(sel, ["stepper", "tol"], lambda r: r["dpos"])
            steps = median_by(sel, ["stepper", "tol"], lambda r: r["steps"])
            for st in steppers:
                pts = sorted((tol, e, steps[(s2, tol)]) for (s2, tol), e in err.items() if s2 == st)
                if not pts:
                    continue
                tols = [x[0] for x in pts]
                axes[0][j].plot(tols, [floor(x[1]) for x in pts], color=color(st, theme), **style(st), ms=3.5)
                axes[1][j].plot(tols, [x[2] for x in pts], color=color(st, theme), **style(st), ms=3.5)
            for i in range(2):
                axes[i][j].set_xscale("log")
                axes[i][j].set_yscale("log")
                axes[i][j].invert_xaxis()
            axes[0][j].set_title(f"{PCOL[p]}, s = {fmt_s(s)}", loc="left", fontsize=10)
            axes[1][j].set_xlabel("step tolerance (tighter to the right)")
        axes[0][0].set_ylabel(f"|Δr| to {what} [mm]")
        axes[1][0].set_ylabel("accepted steps")
        legend_below(fig, axes, steppers, theme)

    figure(name, 2, 3, draw, height=3.0, sharey=False)


def wp_steps(rows, steppers, s, name):
    def draw(fig, axes, theme, t):
        for ax, p in zip(axes[0], moms):
            curves = wp_curves(rows, s, p, "steps")
            for st in steppers:
                if st in curves:
                    c = curves[st]
                    ax.plot([x[0] for x in c], [floor(x[1]) for x in c], color=color(st, theme), **style(st), ms=3.5)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(f"{PCOL[p]}, s = {fmt_s(s)}", loc="left", fontsize=10)
            ax.set_xlabel("accepted steps per track")
        axes[0][0].set_ylabel("|Δr| [mm]")
        legend_below(fig, axes, steppers, theme)

    figure(name, 1, 3, draw, sharey=False)


if hom:
    tol_scan(hom, scanned, 10000.0, "hom-tol", "the analytic helix")
    wp_steps(hom, scanned, 10000.0, "hom-wp-steps")
if inh:
    tol_scan(inh, STEPPERS, 10000.0, "inh-tol", "the reference")
    wp_steps(inh, STEPPERS, 10000.0, "inh-wp-steps")

(OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float))
print("figures:", sorted(p.name for p in OUT.glob("*-light.png")))
