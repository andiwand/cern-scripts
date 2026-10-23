"""Compile diagnostic variants without modifying the production worktree."""

import argparse, json, subprocess, shutil, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--work", type=Path, required=True)
p.add_argument("--source", type=Path, required=True)
a = p.parse_args()
w = a.work
s = a.source
base = w / "runtime-build/pruned-build"
for name in ["core-only", "no-new-birth"]:
    out = w / (name + "-build")
    shutil.copytree(base, out)
    c = json.loads((base / "experiment-build.json").read_text())["command"]
    c = [v.replace(str(base), str(out)) for v in c]
    overlay = out / "overlay"
    overlay.mkdir()
    if name == "core-only":
        subprocess.run(
            ["git", "-C", str(s), "archive", "ae02eeb5fb", "Fatras"],
            stdout=(out / "fatras.tar").open("wb"),
            check=True,
        )
        subprocess.run(
            ["tar", "xf", str(out / "fatras.tar"), "-C", str(overlay)], check=True
        )
        c = [v.replace(str(s / "Fatras"), str(overlay / "Fatras")) for v in c]
        f = out / "runtime-fatras.cpp"
        t = f.read_text()
        begin = t.index("    simulation.charged.interactions.get<StandardScattering>()")
        end = t.index("    if (!cfg.emScattering)", begin)
        t = t[:begin] + t[end:]
        f.write_text(t)
    else:
        for filename, needle in [
            (
                "Ionisation.hpp",
                "    production(result.size() - 1, start + extent * depth);",
            ),
            (
                "ComptonScattering.hpp",
                "    production(generated.size() - 2, distance / depth);",
            ),
        ]:
            rel = Path("ActsFatras/Physics/ElectroMagnetic") / filename
            f = overlay / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            t = (s / "Fatras/include" / rel).read_text()
            assert needle in t
            t = t.replace(
                needle, "    // Diagnostic: omit new charged daughter birth column."
            )
            f.write_text(t)
        c.insert(1, "-I" + str(overlay))
    record = {
        "variant": name,
        "command": c,
        "baseline_revision": "ae02eeb5fbf266fd3ece0a8bea64f1935d453ba9",
    }
    (out / "experiment-build.json").write_text(json.dumps(record, indent=2))
    with (out / "build.log").open("w") as f:
        subprocess.run(c, stdout=f, stderr=subprocess.STDOUT, check=True)
    subprocess.run(
        [
            sys.executable,
            str(
                Path(__file__).resolve().parent.parent
                / "fatras-radiative-secondaries/run.py"
            ),
            "--source",
            str(s),
            "--module",
            str(out),
            "--output",
            str(w / name),
        ],
        check=True,
    )
    print(name, "done", flush=True)
