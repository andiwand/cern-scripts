import json, sys, pathlib
for d in sys.argv[1:]:
    d = pathlib.Path(d); a = json.loads((d / "analysis.json").read_text()); e = json.loads((d / "eff.json").read_text())
    print(f"## {d.name}")
    print("| variant | eff ambi % | fake ambi % | ckf+dup inner wrong % | ambi inner wrong % | ambi inner missing % | wrong pix/1000 | σ68 d0 µm | σ68 z0 µm | |pull d0|>5 % |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for v in sorted((k for k in a if k != "seeds"), key=lambda k: (k.endswith("chi30"), k)):
        if v not in a: continue
        r = a[v]; ih, ai = r["innerHit"], r["ambiInnerHit"]
        pct = lambda h, k: 100 * h[k] / (h["tracks"] - h["nopixel"])
        print(f'| {v} | {100*e[v]["ambi"]["eff_particles"]:.2f} | {100*e[v]["ambi"]["fakeratio_tracks"]:.2f} | {pct(ih,"wrong"):.2f} | {pct(ai,"wrong"):.2f} | {pct(ai,"missing"):.2f} | {1000*ai["wrongPixelHits"]/ai["pixelHits"]:.2f} | {1e3*r["ambiTrack"]["s68_eLOC0"]:.1f} | {1e3*r["ambiTrack"]["s68_eLOC1"]:.1f} | {100*r["ambiTrack"]["tail5_eLOC0"]:.2f} |')
