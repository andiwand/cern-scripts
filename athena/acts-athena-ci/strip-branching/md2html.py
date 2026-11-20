#!/usr/bin/env python3
"""(copy of seed-track-hits/md2html.py with ### headings) Standalone HTML of a TSI note: markdown body with the stylesheet of an earlier note page, PNGs embedded.
Handles headings, paragraphs, nested bullet lists with continuation paragraphs, tables and images.
usage: md2html.py note.md style-template.html out.html [charts.json charts.js]
With charts.json, an image whose alt text names a figure in it becomes an inline SVG chart (charts.js) instead of the PNG."""
import sys, re, html, base64, os
md_path, tpl_path, out_path = sys.argv[1:4]
CH = open(sys.argv[4]).read() if len(sys.argv) > 5 else None
CHJS = open(sys.argv[5]).read() if CH else ""
FIGS = __import__("json").loads(CH)["figs"] if CH else {}
EXTRA = """<style>
:root { --p1l: #9fc3ee; --p2l: #f3a27e; --p3l: #9edcc3; --p4l: #f5c860; --p6: #8a5cc2; --grey: #b4b5ae; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --p1l: #2a5487; --p2l: #8a3d1d; --p3l: #1d6149; --p4l: #7d5a10; --p6: #a07fd6; --grey: #5c5d58; } }
:root[data-theme="dark"] { --p1l: #2a5487; --p2l: #8a3d1d; --p3l: #1d6149; --p4l: #7d5a10; --p6: #a07fd6; --grey: #5c5d58; }
.plot { display: grid; gap: 10px; }
.gridps { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
.colh { font-size: 0.9rem; font-weight: 600; color: var(--fg-2); }
details > .grid2 { margin-top: 10px; }
@media (max-width: 760px) { .gridps { grid-template-columns: minmax(0, 1fr); } .colh { display: none; } } .cap { font-size: 0.82rem; color: var(--fg-2); }
details h4 { font-size: 0.84rem; font-weight: 600; margin: 12px 0 4px; }
</style>"""
base = os.path.dirname(os.path.abspath(md_path))
tpl = open(tpl_path).read()
head = tpl[tpl.index('<link rel="stylesheet"'):tpl.index('</style>') + len('</style>')]

def inline(t):
    codes = []
    def keep(m): codes.append(html.escape(m.group(1))); return f"\0{len(codes)-1}\0"
    t = re.sub(r"`([^`]+)`", keep, t.replace("\\|", "\1"))
    t = html.escape(t, quote=False).replace("\1", "|")
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)          # local links: plain text, not published
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)\*(?![\w*])", r"<em>\1</em>", t)
    return re.sub(r"\0(\d+)\0", lambda m: f"<code>{codes[int(m.group(1))]}</code>", t)
def slug(h): return re.sub("[^a-z0-9]+", "-", h.lower()).strip("-")
cells = lambda l: [c.strip() for c in re.split(r"(?<!\\)\|", l.strip().strip("|"))]
NUM = re.compile(r"^[\d\s.,%/–≥<>()+−-]+$|^\*\*[\d.,%]+\*\*$")

def render_list(lines):
    """lines of a list block -> nested <ul>; an item keeps its paragraphs and sub-items in source order."""
    root = {"ind": -1, "seq": []}; stack = [root]; gap = False
    for l in lines:
        if not l.strip(): gap = True; continue
        ind = len(l) - len(l.lstrip(" ")); s = l.strip()
        if s.startswith("- "):
            while stack[-1]["ind"] >= ind: stack.pop()
            item = {"ind": ind, "seq": [s[2:]]}
            stack[-1]["seq"].append(item); stack.append(item); gap = False
        else:
            while len(stack) > 2 and stack[-1]["ind"] >= ind: stack.pop()
            tgt = stack[-1]
            if gap or not isinstance(tgt["seq"][-1], str): tgt["seq"].append(s)
            else: tgt["seq"][-1] += " " + s
            gap = False
    def emit(seq):
        o = ""; ul = []
        def flush():
            nonlocal o, ul
            if ul: o += "<ul>" + "".join(f"<li>{emit(it['seq'])}</li>" for it in ul) + "</ul>"; ul = []
        for k, x in enumerate(seq):
            if isinstance(x, dict): ul.append(x); continue
            flush(); o += inline(x) if k == 0 else f"<p>{inline(x)}</p>"
        flush(); return o
    return emit(root["seq"])

L = open(md_path).read().split("\n"); i = 0; out = []; title = ""; nav = []
while i < len(L):
    l = L[i]
    if not l.strip(): i += 1; continue
    if l.startswith("# "): title = l[2:]; i += 1; continue
    if l.startswith("### "):
        out.append(f'<h3>{inline(l[4:])}</h3>'); i += 1; continue
    if l.startswith("## "):
        h = l[3:]; nav.append(h); out.append(f'<h2 id="{slug(h)}">{inline(h)}</h2>'); i += 1; continue
    m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", l)
    if m and m.group(1) in FIGS:
        out.append(f'<div class="plot" data-plot="{m.group(1)}"></div>'); i += 1; continue
    if m:
        b64 = base64.b64encode(open(os.path.join(base, m.group(2)), "rb").read()).decode()
        out.append(f'<figure><img alt="{html.escape(m.group(1))}" src="data:image/png;base64,{b64}"></figure>'); i += 1; continue
    if l.startswith("|"):
        rows = []
        while i < len(L) and L[i].startswith("|"): rows.append(L[i]); i += 1
        hdr = cells(rows[0]); body = [cells(r) for r in rows[2:]]
        isnum = [all(NUM.match(r[c]) or not r[c] for r in body if c < len(r)) and c > 0 for c in range(len(hdr))]
        t = "<div class=\"tw\"><table><thead><tr>" + "".join(f'<th{" class=n" if isnum[c] else ""}>{inline(h)}</th>' for c, h in enumerate(hdr)) + "</tr></thead><tbody>"
        for r in body:
            t += "<tr>" + "".join(f'<td{" class=n" if c < len(isnum) and isnum[c] else ""}>{inline(x)}</td>' for c, x in enumerate(r)) + "</tr>"
        out.append(t + "</tbody></table></div>"); continue
    if l.startswith("- "):
        blk = []
        while i < len(L) and (L[i].startswith("- ") or L[i].startswith("  ") or
                              (not L[i].strip() and i + 1 < len(L) and L[i + 1].startswith("  "))):
            blk.append(L[i]); i += 1
        out.append(render_list(blk)); continue
    para = []
    while i < len(L) and L[i].strip() and not L[i].startswith(("|", "- ", "#", "![")): para.append(L[i].strip()); i += 1
    if not para: para.append(L[i].strip()); i += 1
    out.append(f"<p>{inline(' '.join(para))}</p>")

# summary paragraph + its list into the verdict box
for k, blk in enumerate(out):
    if blk.startswith("<p><strong>Summary.</strong>") and k + 1 < len(out) and out[k + 1].startswith("<ul>"):
        out[k] = '<div class="verdict"><h2>Summary</h2>' + out[k + 1] + "</div>"; out[k + 1] = ""; break
NUMPRE = re.compile(r"^[0-9]+[.] ")
navh = "<nav>" + "".join('<a href="#' + slug(h) + '">' + inline(NUMPRE.sub("", h)) + "</a>" for h in nav) + "</nav>"
doc = (f'<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
       f'<title>{html.escape(title)}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n{head}\n{EXTRA if CH else ""}\n'
       f'<div class="wrap">\n<h1>{inline(title)}</h1>\n{navh}\n' + "\n".join(x for x in out if x) + "\n</div>\n" + (f"<script>\nconst CH = {CH};\n{CHJS}</script>\n" if CH else ""))
open(out_path, "w").write(doc)
print(out_path, len(doc) // 1024, "kB")
