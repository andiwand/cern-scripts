#!/usr/bin/env python3
"""Standalone Markdown report with embedded data and interactive SVG figures."""
import argparse
import html
import json
import os
import posixpath
from pathlib import Path
from markdown_it import MarkdownIt

COLORS = ["#263b50", "#227c96", "#d35432"]
FAMILIES = ["core", "previous", "new"]
LABELS = [
    "No tail handling + quality cut",
    "Previous tail handling + quality cut",
    "Tail handling + normalized mixture score",
]


def chart(title, xlabel, ylabel, series, caption=""):
    return dict(
        title=title, xlabel=xlabel, ylabel=ylabel, series=series, caption=caption
    )


def series(label, points, color):
    return dict(label=label, points=points, color=color)


def figures(directory):
    plots = []
    odd = json.loads((directory / "normalized-score-check.json").read_text())
    groups = []
    for family, label, color in zip(FAMILIES, LABELS, COLORS):
        points = []
        for retention in sorted({r["retention"] for r in odd}):
            rows = [
                r for r in odd if r["family"] == family and r["retention"] == retention
            ]
            m, f, t = [
                sum(r["test"][key] for r in rows)
                for key in ["matched", "fakes", "tracks"]
            ]
            points.append(
                dict(
                    x=100 * m / 34306,
                    y=100 * f / t,
                    label=f"Train retention {retention:g}; {m} matched, {f} fakes / {t} tracks",
                )
            )
        groups.append(series(label, points, color))
    plots.append(
        chart(
            "ODD: normalized score, pileup 400",
            "Truth efficiency [%]",
            "Fake tracks / tracks [%]",
            groups,
            "Two-fold held-out totals, 20 previously inspected Fatras events. Exploratory; this is not independent validation.",
        )
    )
    for pu in [200, 400]:
        summary = json.loads((directory / f"pu{pu}/summary.json").read_text())
        pts = []
        for name, label, color in zip(
            ["core15", "tail", "tail80"],
            [
                "No tail handling",
                "Previous tail handling",
                "Tail + live absolute T ≤ 80",
            ],
            COLORS,
        ):
            d = summary["variants"][name + "_ambi"]
            pts.append(
                series(
                    label,
                    [
                        dict(
                            x=100 * d["efficiency"],
                            y=100 * d["fake_fraction"],
                            label=label,
                        )
                    ],
                    color,
                )
            )
        plots.append(
            chart(
                f"ODD: original three-mode comparison, pileup {pu}",
                "Truth efficiency [%]",
                "Fake tracks / tracks [%]",
                pts,
                "Initial absolute-budget implementation; distinct from the later normalized final score.",
            )
        )
    athena = directory / "athena/validation.json"
    if athena.exists():
        d = json.loads(athena.read_text())
        groups = []
        for family, label, color in zip(FAMILIES, LABELS, COLORS):
            pts = []
            for retention, point in d["points"].items():
                if family not in point["groups"]:
                    continue
                c = point["groups"][family]
                v = c["validation"]
                pts.append(
                    dict(
                        x=100 * v["efficiency"],
                        y=100 * v["fake_rate"],
                        label=f"Train retention {retention}; {c['variant']}, {c['metric']} ≤ {c['cut']:.4g}; {v['matched']} matched, {v['fakes']} fakes / {v['tracks']} tracks",
                    )
                )
            groups.append(series(label, pts, color))
        plots.insert(
            0,
            chart(
                f"Athena ITk: independent validation, {d['events']} events",
                "Truth efficiency [%]",
                "Fake tracks / tracks [%]",
                groups,
                "All working points fixed on the separate training sample. Lines connect discrete operating points; they are not fitted ROC curves.",
            ),
        )
        for field, error, label in [
            ("efficiency_change_pp", "efficiency_se_pp", "Efficiency difference [pp]"),
            ("fake_rate_change_pp", "fake_rate_se_pp", "Fake-rate difference [pp]"),
        ]:
            groups = []
            for comparison, name, color in [
                ("new-core", "New score minus Gaussian", COLORS[0]),
                ("new-previous", "New score minus previous tails", COLORS[1]),
            ]:
                points = []
                for retention, point in d["points"].items():
                    if comparison not in point["paired"]:
                        continue
                    r = point["paired"][comparison]["rates"]
                    points.append(
                        dict(
                            x=100 * float(retention),
                            y=r[field],
                            error=r[error],
                            label=f"{r[field]:.5f} ± {r[error]:.5f} pp (one SE)",
                        )
                    )
                groups.append(series(name, points, color))
            plots.append(
                chart(
                    "Athena paired comparison: " + label,
                    "Training matched-particle retention [%]",
                    label,
                    groups,
                    "Error bars: one event-cluster standard error on each paired difference; pointwise, not simultaneous intervals.",
                )
            )
        point = d["points"]["0.995"]
        for field, label, scale in [
            ("d0res", "d₀ [µm]", 1000),
            ("z0res", "z₀ [µm]", 1000),
            ("qptres", "Relative q/pT [%]", 100),
        ]:
            groups = []
            for family, name, color in zip(FAMILIES, LABELS, COLORS):
                if family not in point["groups"]:
                    continue
                r = point["groups"][family]["common_resolutions"][field]
                pts = [
                    dict(
                        x=q, y=scale * r[k], label=f"{name}; {q}% interval, N={r['n']}"
                    )
                    for q, k in [(68.27, "width68"), (95, "width95")]
                ]
                groups.append(series(name, pts, color))
            plots.append(
                chart(
                    "Athena common-truth resolution: " + label,
                    "Central interval coverage [%]",
                    "Half-width: " + label,
                    groups,
                    "99.5% training-retention point. One best-probability track per common truth particle; prompt production radius < 0.1 mm.",
                )
            )
    diagnostics = directory / "athena/diagnostics.json"
    if diagnostics.exists():
        d = json.loads(diagnostics.read_text())
        for metric, title, ylabel in [
            (
                "efficiency",
                "Truth efficiency versus pseudorapidity",
                "Truth efficiency [%]",
            ),
            (
                "fake_rate",
                "Fake rate versus pseudorapidity",
                "Fake tracks / tracks [%]",
            ),
        ]:
            groups = []
            for family, label, color in zip(FAMILIES, LABELS, COLORS):
                r = d["groups"][family][metric]["eta"]
                points = [
                    dict(
                        x=(lo + hi) / 2,
                        y=100 * passed / total,
                        label=f"{lo:g} ≤ |η| < {hi:g}: {passed} / {total}",
                    )
                    for lo, hi, passed, total in zip(
                        r["edges"][:-1], r["edges"][1:], r["passed"], r["total"]
                    )
                    if total
                ]
                groups.append(series(label, points, color))
            plots.append(
                chart(
                    "Athena: " + title,
                    "|η|",
                    ylabel,
                    groups,
                    "99.5% training-retention point; descriptive binned rates. Exact counts appear in the point tooltips.",
                )
            )
    nn_path = directory / "athena/nn-validation.json"
    if nn_path.exists():
        nn = json.loads(nn_path.read_text())
        raw = json.loads((directory / "athena/validation.json").read_text())
        nn_plots = []
        for title, specifications in [
            (
                "NN before selection: three tail modes",
                [
                    (nn, f, l, c)
                    for f, l, c in zip(
                        FAMILIES,
                        [
                            "NN + nominal CKF + χ² cut",
                            "NN + previous tails + χ² cut",
                            "NN + tails + mixture score",
                        ],
                        COLORS,
                    )
                ],
            ),
            (
                "Effect of NN calibration at common training targets",
                [
                    (raw, "core", "Raw Gaussian + quality cut", COLORS[0]),
                    (nn, "core", "NN + nominal CKF + χ² cut", COLORS[1]),
                    (nn, "new", "NN tails + mixture score", COLORS[2]),
                ],
            ),
        ]:
            groups = []
            for study, family, label, color in specifications:
                points = []
                for retention, point in study["points"].items():
                    if family not in point["groups"]:
                        continue
                    c = point["groups"][family]
                    v = c["validation"]
                    points.append(
                        dict(
                            x=100 * v["efficiency"],
                            y=100 * v["fake_rate"],
                            label=f"Train retention {retention}; {c['variant']}, {c['metric']} ≤ {c['cut']:.4g}; {v['matched']} matched, {v['fakes']} fakes / {v['tracks']} tracks",
                        )
                    )
                groups.append(series(label, points, color))
            nn_plots.append(
                chart(
                    "Athena ITk: " + title,
                    "Truth efficiency [%]",
                    "Fake tracks / tracks [%]",
                    groups,
                    "All-charge/all-size pixel NN before selection, primary only. Nominal CKF includes the extended 14/20σ gate scan. Same training match targets; choices fixed on 200 events and evaluated on 800 separate events. Exploratory follow-up on an already inspected sample.",
                ),
            )
        plots = nn_plots + plots
    scan_path = directory / "athena/hole-scan/validation.json"
    if scan_path.exists():
        scan = json.loads(scan_path.read_text())
        groups = []
        for family, label, color in zip(FAMILIES, LABELS, COLORS):
            points = []
            for retention, point in scan["points"].items():
                c = point["groups"][family]
                v = c["validation"]
                points.append(
                    dict(
                        x=100 * v["efficiency"],
                        y=100 * v["fake_rate"],
                        label=f"Target {retention}; {c['variant']}; {c['metric']} ≤ {c['cut']:.5g}; {v['matched']} matches, {v['fakes']} fakes",
                    )
                )
            groups.append(series(label, points, color))
        previous = json.loads(
            (directory / "athena/nn-extended/validation.json").read_text()
        )
        groups.append(
            series(
                "Nominal before hole/outlier scan",
                [
                    dict(
                        x=100 * p["groups"]["core"]["validation"]["efficiency"],
                        y=100 * p["groups"]["core"]["validation"]["fake_rate"],
                        label=f"Earlier nominal; target {r}",
                    )
                    for r, p in previous["points"].items()
                ],
                "#888888",
            )
        )
        scan_plots = [
            chart(
                "Athena ITk: hole/outlier scan, pT selection unchanged",
                "Truth efficiency [%]",
                "Fake tracks / tracks [%]",
                groups,
                "All modes use NN pre-calibration. Equal local scan structure, choices fixed on 200 training events; 800 previously inspected evaluation events. Exploratory. Lines connect discrete points.",
            )
        ]
        groups = []
        for comparison, label, color in [
            ("new-core", "Tail score minus nominal", COLORS[0]),
            ("new-previous", "Tail score minus previous tails", COLORS[1]),
        ]:
            points = []
            for retention, point in scan["points"].items():
                r = point["paired"][comparison]["rates"]
                points.append(
                    dict(
                        x=100 * float(retention),
                        y=r["fake_rate_change_pp"],
                        error=r["fake_rate_se_pp"],
                        label=f"Fake-rate Δ {r['fake_rate_change_pp']:+.5f} ± {r['fake_rate_se_pp']:.5f} pp; efficiency Δ {r['efficiency_change_pp']:+.5f} ± {r['efficiency_se_pp']:.5f} pp",
                    )
                )
            groups.append(series(label, points, color))
        scan_plots.append(
            chart(
                "Hole/outlier scan: paired fake-rate differences",
                "Training matched-particle retention [%]",
                "Fake-rate difference [pp]",
                groups,
                "Bars show one paired event-cluster SE. Evaluation efficiencies can differ: hover/focus for their paired differences. These are not simultaneous scan intervals.",
            )
        )
        plots = scan_plots + plots
    return plots


p = argparse.ArgumentParser()
p.add_argument("note", type=Path)
p.add_argument("--output", type=Path)
p.add_argument(
    "--report-text",
    type=Path,
    help="Concise report source; notebook remains the artifact index",
)
a = p.parse_args()
directory = a.note.with_suffix("")
plots = figures(directory)
md = MarkdownIt("commonmark", {"html": False}).enable("table")
source = a.report_text or a.note
out = a.output or a.note.with_suffix(".html")
tokens = md.parse(source.read_text().replace(".png)", ".pdf)"))
link_base = os.path.relpath(source.parent, out.parent)
for token in tokens:
    for child in token.children or []:
        if child.type == "link_open":
            href = child.attrGet("href")
            if (
                href
                and not href.startswith(("#", "/", "mailto:"))
                and "://" not in href
            ):
                child.attrSet(
                    "href", posixpath.normpath(posixpath.join(link_base, href))
                )
body = md.renderer.render(tokens, md.options, {})
body = body[body.index("</h1>") + 5 :]
css = """body{font:16px/1.55 system-ui,sans-serif;max-width:1120px;margin:32px auto;padding:0 22px;color:#23333d;background:#fff}h1{font-size:2rem;line-height:1.2}h2{margin-top:2.2em}a{color:#126b84}pre{background:#f2f5f7;padding:14px;overflow:auto}code{font-size:.88em}table{border-collapse:collapse;font-size:14px;width:100%;display:block;overflow:auto}th,td{padding:7px 12px;border-bottom:1px solid #dce3e7;white-space:nowrap}th{background:#eef3f5}li{margin:5px 0}.figure{margin:25px 0;border:1px solid #dce3e7;border-radius:8px;padding:18px}.figure h3{margin:0 0 8px}.caption{font-size:13px;color:#57656d}svg{width:100%;height:auto;overflow:visible}.legend{display:flex;flex-wrap:wrap;gap:12px;font-size:13px}.legend label{cursor:pointer}button,select{font:inherit;padding:6px 10px;border:1px solid #b7c4cb;border-radius:4px;background:white;margin:5px}circle:focus{stroke:black;stroke-width:3}summary{cursor:pointer;font-weight:600;padding:10px 0}nav{display:flex;gap:20px;flex-wrap:wrap}.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}@media print{button,.legend{display:none}details{display:block}.figure{break-inside:avoid}body{max-width:none}}"""
js = Path(__file__).with_name("report.js").read_text()
summary = ""
validation_path = directory / "athena/validation.json"
if validation_path.exists():
    original = json.loads(validation_path.read_text())["points"]["0.995"]["paired"]
    r = original["new-core"]["rates"]
    summary += (
        f"<p><strong>Original 800-event comparison:</strong> the new score improves on previous tail handling, "
        f"but its central values do not beat tuned Gaussian tracking: efficiency "
        f'{r["efficiency_change_pp"]:+.5f} ± {r["efficiency_se_pp"]:.5f} percentage points; '
        f'fake rate {r["fake_rate_change_pp"]:+.5f} ± {r["fake_rate_se_pp"]:.5f} pp '
        f"(paired standard errors, main working point).</p>"
    )
cross_path = directory / "athena/nn-cross-calibration.json"
if cross_path.exists():
    cross = json.loads(cross_path.read_text())
    r = cross["paired"]["nn-new minus nn-core"]
    summary += (
        f"<p><strong>All-charge NN before selection, plus tail score:</strong> versus independently tuned NN + nominal CKF, "
        f'efficiency {r["efficiency_change_pp"]:+.5f} ± {r["efficiency_se_pp"]:.5f} pp; '
        f'fake rate {r["fake_rate_change_pp"]:+.5f} ± {r["fake_rate_se_pp"]:.5f} pp. '
        f"Cuts use separate training events; this follow-up reuses the inspected sample.</p>"
    )
    rows = []
    for key, label in [
        ("nn-core", "NN + nominal CKF + χ² cut"),
        ("nn-previous", "NN + previous tails + χ² cut"),
        ("nn-new", "NN + tails + mixture score"),
    ]:
        c = cross["counts"][key]
        rows.append(
            f"<tr><td>{label}</td><td>{100*c['efficiency']:.5f}%</td>"
            f"<td>{c['fakes']:,} / {c['tracks']:,}</td><td>{100*c['fake_rate']:.5f}%</td></tr>"
        )
    summary += (
        "<table><thead><tr><th>Main working point</th><th>Efficiency</th>"
        "<th>Fakes / tracks</th><th>Fake rate</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )
if (directory / "athena/gun-delta-results.json").exists():
    summary += (
        "<p><strong>Direct cluster check:</strong> NN pre-calibration recovers all six delta-like muons "
        "lost when tightening the raw hit gate, but loses five other matches: net +1 out of 5,000. "
        "The mechanism is visible; its net benefit depends on the rest of the sample.</p>"
    )
extra_figures = ""
report_label = "Full notebook entry, methods and review record"
if a.report_text:
    # The concise source owns the findings; avoid repeating the generated summary.
    split = body.index("<h2>")
    summary, body = body[:split], body[split:]
    report_label = "Results, methods and review record"
    extra_figures = '<details><summary>Additional diagnostic and earlier ODD figures</summary><section id="more-figures"></section></details>'
heading = html.escape(source.read_text().splitlines()[0].lstrip("# "))
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{heading}</title><style>{css}</style></head><body>
<h1>{heading}</h1><p>27 November 2026 · ODD and Athena ITk study</p>
<nav><a href="#figures">Interactive figures</a><a href="#note">Results and methods</a><button id="data">Download plot data</button></nav>
<p class="caption">Figures use SVG. Toggle series with the legend; hover or focus a point for its exact values. All chart data and scripts are embedded for offline use.</p>
{summary}
<section id="figures" aria-label="Interactive scientific figures"></section>
<details id="note" open><summary>{report_label}</summary>{body}</details>
{extra_figures}
<script id="plot-data" type="application/json">{json.dumps(plots,allow_nan=False).replace('</','<\\/')}</script><script>{js}</script></body></html>'''
out.write_text(page)
print(out, len(page), "bytes;", len(plots), "SVG figures; no bitmap figures")
