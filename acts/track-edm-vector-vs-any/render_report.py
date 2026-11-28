"""Render this study's Markdown subset and measured plot as offline static HTML.

Usage: python render_report.py /path/to/2026-10-31_track-edm-vector-vs-any.md
The note's companion folder must contain timing-summary.json.
"""

import html
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

note = Path(sys.argv[1])
assets = note.with_suffix("")
timing = json.loads((assets / "timing-summary.json").read_text())
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), layout="constrained", sharex=True)
for ax, (workload, title) in zip(axes, [("muons", "200 muons/event"), ("ttbar-pu200", "ttbar + 200 pileup")]):
    ax.axvline(0, color="#768694", ls="--", lw=1)
    for y, variant, label, color in [(1, "vector", "Vector", "#1f5f8b"), (0, "any", "Any", "#b3362f")]:
        points = 100 * (np.array(timing[workload][variant]["paired_ckf_ratios"]) - 1)
        median = 100 * (timing[workload][variant]["median_ratio"] - 1)
        ax.plot([min(points), max(points)], [y, y], color=color, alpha=.5)
        ax.scatter(points, y + np.linspace(-.12, .12, len(points)), color=color, s=25, alpha=.7)
        ax.scatter([median], [y], marker="D", s=65, color=color, edgecolor="white", zorder=4)
        ax.annotate(f"{median:+.1f}%", (median, y), xytext=(0, 20), textcoords="offset points", ha="center", color=color, weight="bold")
    ax.set(title=title, yticks=[0, 1], yticklabels=["Any", "Vector"], ylim=(-.45, 1.65), xlim=(-10, 31), xlabel="CKF time change vs main (%)")
    ax.grid(axis="x", alpha=.15)
    ax.spines[["top", "right", "left"]].set_visible(False)
fig.suptitle("Six paired process comparisons • lower is faster", fontsize=13)
for suffix in ["svg", "png"]:
    fig.savefig(assets / f"ckf-runtime.{suffix}", dpi=180, facecolor="white")
plt.close(fig)


def inline(text):
    """Inline markup used in the companion note; escape all source HTML."""
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"(?<![\w\"=])(https://[^\s<]+)", r'<a href="\1">\1</a>', text)
    return text


def render(source):
    blocks = []
    for block in re.split(r"\n\s*\n", source.strip()):
        lines = block.splitlines()
        if lines[0].startswith("#"):
            for line in lines:
                match = re.fullmatch(r"(#{1,6}) (.*)", line)
                if not match:
                    raise ValueError(f"Unsupported heading block: {block}")
                level, title = len(match[1]), match[2]
                anchor = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
                blocks.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
        elif lines[0].startswith("| "):
            rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
            head = "".join(f"<th>{inline(cell)}</th>" for cell in rows[0])
            body = "".join("<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>" for row in rows[2:])
            blocks.append(f'<div class="tablewrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
        elif lines[0].startswith("- "):
            items = re.split(r"\n- ", block[2:])
            blocks.append("<ul>" + "".join(f"<li>{inline(' '.join(item.splitlines()))}</li>" for item in items) + "</ul>")
        elif lines[0].startswith("!["):
            match = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", block)
            if not match:
                raise ValueError(block)
            # Embed the plot so the HTML works without network or companion files.
            svg = (note.parent / match[2]).read_text()
            svg = svg[svg.index("<svg"):]
            svg = svg.replace("<svg ", f'<svg role="img" aria-label="{html.escape(match[1], quote=True)}" ', 1)
            blocks.append(f'<figure>{svg}<figcaption>{html.escape(match[1])}</figcaption></figure>')
        else:
            blocks.append("<p>" + inline(" ".join(lines)) + "</p>")
    return "\n".join(blocks)


css = """
:root{--bg:#f5f7f9;--panel:#fff;--fg:#15202b;--secondary:#4c5a67;--line:#d7dde3;--accent:#1f5f8b}
@media(prefers-color-scheme:dark){:root{--bg:#14181d;--panel:#1c2229;--fg:#e8ecf0;--secondary:#b4bec8;--line:#313b45;--accent:#6fb0e0;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,-apple-system,sans-serif;padding:24px 16px 64px}
main{max-width:1040px;margin:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:28px 32px}
h1{font-size:1.9rem;line-height:1.2;margin:0 0 8px;letter-spacing:-.02em}h2{color:var(--secondary);font-size:1rem;font-weight:500;margin:0 0 24px}
h3{font-size:1.25rem;line-height:1.3;margin:32px 0 12px;border-top:1px solid var(--line);padding-top:20px}
p,ul{margin:0 0 14px;max-width:90ch}li{margin-bottom:7px}a{color:var(--accent);overflow-wrap:anywhere}code{font: .87em ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere}
.tablewrap{overflow-x:auto;margin:16px 0 20px}table{border-collapse:collapse;width:100%;font-size:.86rem;font-variant-numeric:tabular-nums}th,td{text-align:left;padding:9px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--secondary);white-space:nowrap}
figure{margin:20px 0}figure svg{display:block;width:100%;height:auto;background:white;border-radius:6px}figcaption{font-size:.85rem;color:var(--secondary);margin-top:7px}
nav{max-width:1040px;margin:0 auto 16px;font-size:.85rem}footer{color:var(--secondary);font-size:.8rem;margin:24px auto;max-width:1040px}
@media(max-width:600px){main{padding:20px 16px}body{padding:12px 8px}h1{font-size:1.5rem}}
@media print{body{background:white;color:black;padding:0}main{border:0;padding:0}nav,footer{display:none}h3{break-after:avoid}table,figure{break-inside:avoid}a{color:inherit}}
"""
page = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Track EDM: concrete vector vs Any — 31.10.2026</title><style>{css}</style></head>
<body><nav>ACTS notebook · 31.10.2026 · <a href="{note.name}">Markdown source</a> · <a href="#runtime">Runtime</a> · <a href="#recommendation">Recommendation</a></nav>
<main>{render(note.read_text())}</main><footer>Local experiment · Static offline report · No external assets or scripts</footer></body></html>
'''
note.with_suffix(".html").write_text(page)
print(note.with_suffix(".html"))
