import pathlib, sys
N = pathlib.Path(sys.argv[1])
css = (N / "base.css").read_text().replace("<style>", "").replace("</style>", "")
css += """
/* figures: inline SVG styled by the theme tokens */
figure { margin: 0; display: grid; gap: 8px; }
.fig { overflow-x: auto; background: var(--paper); border: 1px solid var(--rule); border-radius: 6px; padding: 10px; }
.fig svg { display: block; width: 100%; min-width: 560px; height: auto; font-family: var(--font-body); }
figcaption { font-size: 13px; color: var(--muted); }
svg .grid { stroke: var(--rule); stroke-width: 1; }
svg .tick, svg .axis, svg .edgelab { fill: var(--muted); font-size: 12px; }
svg .axis { font-size: 13px; }
svg .cut { stroke: var(--muted); stroke-dasharray: 5 4; stroke-width: 1.2; }
svg .cutlab { fill: var(--muted); font-size: 11.5px; }
svg .core { fill: none; stroke: var(--bad); stroke-width: 2.2; }
svg .mix { fill: none; stroke: var(--accent); stroke-width: 2.6; }
svg .corelab { fill: var(--bad); font-size: 13px; font-weight: 600; }
svg .mixlab { fill: var(--accent); font-size: 13px; font-weight: 600; }
svg .drop { stroke: var(--muted); stroke-width: 1; stroke-dasharray: 2 3; }
svg .hitcore { fill: var(--paper); stroke: var(--bad); stroke-width: 2; }
svg .hitmix { fill: var(--accent); stroke: var(--paper); stroke-width: 1.5; }
svg .wlab { fill: var(--ink); font-size: 11.5px; font-family: var(--font-mono); }
svg .lane { fill: var(--ink); font: 600 14px var(--font-display); }
svg .node { fill: var(--code-bg); stroke: var(--rule); stroke-width: 1.2; }
svg .node.bad { stroke: var(--bad); }
svg .node.good { fill: var(--good-bg); stroke: var(--good); }
svg .nodetext { fill: var(--ink); font-size: 12.5px; }
svg .edge { stroke: var(--muted); stroke-width: 1.4; fill: none; }
svg .ahead { fill: var(--muted); }
td.l, th.l { text-align: left; }
"""
flow = (N / "flow.svg").read_text()
chi2 = (N / "chi2.svg").read_text()
body = (N / "body.html").read_text().replace("{{FLOW}}", flow).replace("{{CHI2}}", chi2)
head = """<title>Scattering Tail Mixture Implementation</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&display=swap">
"""
(N / "out.html").write_text(head + "<style>" + css + "</style>\n" + body)
