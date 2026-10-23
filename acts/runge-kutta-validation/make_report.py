"""Single-file HTML report for the Runge-Kutta stepper validation.

    uv run --with pillow make_report.py PLOT_DIR CONTENT.html OUT.html

PLOT_DIR holds <figure>-light.png and <figure>-dark.png from plot.py.
CONTENT.html is the hand-written body. Each `<!--fig:NAME|ALT-->` in it
becomes a theme-aware figure with both PNGs embedded as data URIs.
"""

import base64
import io
import re
import sys
from pathlib import Path

from PIL import Image

PLOTS = Path(sys.argv[1])
CONTENT = Path(sys.argv[2]).read_text()
OUT = Path(sys.argv[3])


def data_uri(path):
    # A palette PNG is about three times smaller and looks the same for
    # flat line plots
    img = Image.open(path).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def figure(match):
    name, alt = match.group(1), match.group(2)
    light = data_uri(PLOTS / f"{name}-light.png")
    dark = data_uri(PLOTS / f"{name}-dark.png")
    return (
        f'<div class="plot" id="fig-{name}">'
        f'<img class="plot-light" src="{light}" alt="{alt}" loading="lazy">'
        f'<img class="plot-dark" src="{dark}" alt="{alt}" loading="lazy">'
        f"</div>"
    )


body = re.sub(r"<!--fig:([a-z0-9-]+)\|(.*?)-->", figure, CONTENT)

STYLE = """
<title>Generic Runge-Kutta Validation</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
<style>
/* Layout: one reading column with full-width figures; a sticky contents rail on wide screens */
:root {
  --bg: #f4f6f8;
  --paper: #fbfcfd;
  --ink: #14181f;
  --muted: #5b6472;
  --rule: #d9dee5;
  --accent: #1f5f8b;
  --warn: #9a4a00;
  --warn-bg: #fff3e6;
  --font-display: "IBM Plex Sans Condensed", "Arial Narrow", sans-serif;
  --font-body: "IBM Plex Sans", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0f1318; --paper: #151a21; --ink: #e8ebef; --muted: #a3acb8; --rule: #2c343f;
    --accent: #7db4dc; --warn: #f0a868; --warn-bg: #2a1e12; color-scheme: dark;
  }
  :root:not([data-theme="light"]) .plot-light { display: none; }
  :root:not([data-theme="light"]) .plot-dark { display: block; }
}
:root[data-theme="dark"] {
  --bg: #0f1318; --paper: #151a21; --ink: #e8ebef; --muted: #a3acb8; --rule: #2c343f;
  --accent: #7db4dc; --warn: #f0a868; --warn-bg: #2a1e12; color-scheme: dark;
}
:root[data-theme="dark"] .plot-light { display: none; }
:root[data-theme="dark"] .plot-dark { display: block; }
.plot-dark { display: none; }
.plot-light { display: block; }

body { background: var(--bg); color: var(--ink); font: 400 15px/1.6 var(--font-body); }
.wrap {
  max-width: 1180px; margin: 0 auto;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 32px 64px;
  display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 40px;
}
nav.toc { position: sticky; top: calc(env(safe-area-inset-top, 0px) + 24px); align-self: start; font-size: 13px; }
nav.toc ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
nav.toc a { color: var(--muted); text-decoration: none; }
nav.toc a:hover, nav.toc a:focus-visible { color: var(--accent); }
nav.toc .label { font: 600 11px/1 var(--font-display); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; display: block; }
main { min-width: 0; }
header.top { display: grid; gap: 10px; margin-bottom: 28px; }
.eyebrow { font: 500 12px/1 var(--font-mono); color: var(--muted); letter-spacing: .02em; }
h1 { font: 600 clamp(28px, 4vw, 40px)/1.1 var(--font-display); margin: 0; text-wrap: balance; }
h2 { font: 600 24px/1.2 var(--font-display); margin: 0; text-wrap: balance; }
h3 { font: 600 17px/1.3 var(--font-display); margin: 0; }
p, li { max-width: 72ch; }
p { margin: 0; }
a { color: var(--accent); }
code, .mono { font: 400 13px/1.5 var(--font-mono); }
section { display: grid; gap: 16px; padding-block: 28px; border-top: 1px solid var(--rule); }
ul { margin: 0; padding-left: 20px; display: grid; gap: 6px; }
.verdict { font-weight: 500; }
.plot { background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 8px; overflow-x: auto; }
.plot img { width: 100%; max-width: 100%; height: auto; min-width: 640px; }
.caption { font-size: 13px; color: var(--muted); max-width: 90ch; }
.callout { background: var(--warn-bg); border-left: 3px solid var(--warn); padding: 14px 16px; border-radius: 4px; display: grid; gap: 8px; }
.callout h3 { color: var(--warn); }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; min-width: 520px; }
th, td { text-align: left; padding: 6px 12px 6px 0; border-bottom: 1px solid var(--rule); vertical-align: top; }
th { font: 600 12px/1.3 var(--font-display); letter-spacing: .04em; text-transform: uppercase; color: var(--muted); }
td.num { text-align: right; font-family: var(--font-mono); font-size: 12.5px; }
.keys { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.key { background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 12px 14px; display: grid; gap: 4px; align-content: start; }
.key b { font: 600 15px/1.3 var(--font-display); }
.key span { font-size: 13.5px; color: var(--muted); }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
@media (max-width: 860px) {
  .wrap { grid-template-columns: minmax(0, 1fr); gap: 0; }
  nav.toc { display: none; }
}
</style>
"""

OUT.write_text(STYLE + body)
print(f"{OUT}: {OUT.stat().st_size / 1e6:.2f} MB")
