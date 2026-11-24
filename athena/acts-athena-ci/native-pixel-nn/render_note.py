#!/usr/bin/env python3
"""Render the editable study Markdown into a standalone HTML report."""
from pathlib import Path
import base64
import re
import markdown
import sys
from html import escape

note = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'notes/atlas/tsi/notebook/2026-11-24_native-pixel-nn.md'
body = markdown.markdown(note.read_text(), extensions=['tables', 'fenced_code', 'md_in_html'])
def embed(match):
    path=note.parent/match.group(1)
    if path.is_file() and path.suffix=='.png':
        return 'src="data:image/png;base64,'+base64.b64encode(path.read_bytes()).decode()+'"'
    return match.group(0)
body=re.sub(r'src="([^"]+)"',embed,body)
style = '''body{font:16px/1.55 system-ui,sans-serif;color:#182431;background:#f7f8fa;margin:auto;padding:32px 22px;max-width:1050px}h1,h2{line-height:1.2}h1{font-size:2rem}h2{margin-top:2rem}a{color:#145e93}table{border-collapse:collapse;width:100%;display:block;overflow:auto;background:white}th,td{padding:8px 12px;border-bottom:1px solid #d8e0e8;text-align:left}code{font-size:.87em;overflow-wrap:anywhere}li{margin:.4rem 0}img{max-width:100%}details{background:white;padding:12px;border:1px solid #d8e0e8;margin:1rem 0}summary{cursor:pointer;font-weight:600}@media(max-width:600px){body{padding:18px 12px;font-size:15px}th,td{padding:6px}}'''
note.with_suffix('.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+escape(note.read_text().splitlines()[0].removeprefix("# "))+'</title><style>'+style+'</style><main>'+body+'</main></html>\n')
print(note)
print(note.with_suffix('.html'))
