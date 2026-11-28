#!/usr/bin/env python3
"""Two-fold ODD check of dimension-normalized scores against tuned baselines."""
import argparse
import json
from pathlib import Path
import awkward as ak
import numpy as np
import uproot

parser = argparse.ArgumentParser()
parser.add_argument("run", type=Path)
args = parser.parse_args()
p = args.run
diag = [json.loads(line) for line in (p / "diagnostics.jsonl").read_text().splitlines()]


def load(mode):
    a = uproot.open(p / f"{mode}_ambi_tracks.root")["tracksummary"].arrays()
    names = ["track_nr", "trackClassification", "t_pT", "chi2Sum", "NDF"] + [
        "majorityParticleId_" + b
        for b in [
            "vertex_primary",
            "vertex_secondary",
            "particle",
            "generation",
            "sub_particle",
        ]
    ]
    f = {k: ak.to_numpy(ak.flatten(a[k])) for k in names}
    e = np.repeat(ak.to_numpy(a["event_nr"]), ak.to_numpy(ak.num(a["track_nr"])))
    keys = list(zip(e, *(f[k] for k in names[5:])))
    sel = np.isin(f["trackClassification"], [1, 2]) & np.isfinite(f["t_pT"])
    fake = f["trackClassification"] == 3
    lookup = {
        (x["event"], r[0]): r[1] for x in diag for r in x["tracks"][mode + "_ambi"]
    }
    T = np.array([lookup[int(ev), int(i)] for ev, i in zip(e, f["track_nr"])])
    return dict(
        event=e, keys=keys, selected=sel, fake=fake, chi2=f["chi2Sum"], D=f["NDF"], T=T
    )


data = {m: load(m) for m in ["core15", "core25", "core49", "tail"]}


def metrics(d, keep):
    found = {k for k, m in zip(d["keys"], keep & d["selected"]) if m}
    return dict(
        matched=len(found), fakes=int((keep & d["fake"]).sum()), tracks=int(keep.sum())
    )


def cutoff(d, score, train, target):
    best = {}
    for k, v, m in zip(d["keys"], score, train & d["selected"]):
        if m:
            best[k] = min(best.get(k, np.inf), v)
    values = np.sort(list(best.values()))
    return values[target - 1] if len(values) >= target else None


out = []
for fold in ["first10", "last10"]:

    def train_mask(d):
        return d["event"] < 10 if fold == "first10" else d["event"] >= 10

    base = metrics(data["tail"], train_mask(data["tail"]))["matched"]
    for retention in [1, 0.998, 0.995, 0.99, 0.985]:
        target = int(np.ceil(base * retention))
        for family, modes, scores in [
            ("core", ["core15", "core25", "core49"], ["chi2", "chi2_D"]),
            ("previous", ["tail"], ["chi2", "chi2_D"]),
            ("new", ["tail"], ["T_D"]),
        ]:
            trials = []
            for mode in modes:
                d = data[mode]
                train = train_mask(d)
                for kind in scores:
                    score = (
                        d["chi2"]
                        if kind == "chi2"
                        else (
                            d["chi2"] / d["D"] if kind == "chi2_D" else d["T"] / d["D"]
                        )
                    )
                    cut = cutoff(d, score, train, target)
                    if cut is None:
                        continue
                    keep = score <= cut
                    tr = metrics(d, keep & train)
                    trials.append(
                        dict(
                            fold=fold,
                            retention=retention,
                            family=family,
                            mode=mode,
                            score=kind,
                            cut=float(cut),
                            train=tr,
                            test=metrics(d, keep & ~train),
                        )
                    )
            if trials:
                out.append(
                    min(
                        trials,
                        key=lambda t: (t["train"]["fakes"], -t["train"]["matched"]),
                    )
                )
print(json.dumps(out, indent=2))
