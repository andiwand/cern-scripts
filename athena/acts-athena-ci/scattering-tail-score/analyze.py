#!/usr/bin/env python3
"""Freeze training-only choices; evaluate independent, paired validation events."""
import argparse
import json
from pathlib import Path
import numpy as np
import tempfile

PDT = [
    ("run", "u8"),
    ("event", "u8"),
    ("id", "u8"),
    ("pt", "f8"),
    ("eta", "f8"),
    ("hs", "i4"),
    ("radius", "f8"),
]
RDT = [("run", "u8"), ("event", "u8"), ("index", "u8"), ("id", "u8")] + [
    (x, "f8")
    for x in [
        "prob",
        "pt",
        "eta",
        "chi2",
        "ndf",
        "score",
        "dim",
        "weight",
        "logl",
        "d0res",
        "z0res",
        "qptres",
        "phi",
        "d0",
        "z0",
        "qop",
        "theta",
    ]
]
EDT = [("run", "u8"), ("event", "u8"), ("particles", "u8"), ("tracks", "u8")]


def load(directory):
    directory = Path(directory)
    cache = directory / "rows.npz"
    if cache.exists():
        with np.load(cache) as f:
            return {k: f[k] for k in f.files}
    rows = {c: [] for c in "PRE"}
    with (directory / "rows.tsv").open() as f:
        for line in f:
            c, *values = line.split()
            rows[c].append(tuple(values))
    data = {
        c: np.array(rows[c], dtype=dt) for c, dt in [("P", PDT), ("R", RDT), ("E", EDT)]
    }
    for c in data:
        data[c].sort(
            order=["run", "event"]
            + (["id"] if c == "P" else ["index"] if c == "R" else [])
        )
    assert len(np.unique(data["E"][["run", "event"]])) == len(data["E"])
    # Publish only a complete cache when independent analyses overlap.
    with tempfile.NamedTemporaryFile(dir=directory, suffix=".npz", delete=False) as f:
        temporary = Path(f.name)
        try:
            np.savez_compressed(f, **data)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(cache)
    return data


def keys(a):
    return a[["run", "event", "id"]].tolist()


def values(r, metric):
    if metric == "none":
        return np.zeros(len(r))
    if metric == "chi2":
        return r["chi2"]
    if metric == "chi2/dim":
        return r["chi2"] / r["dim"]
    if metric == "score/dim":
        return r["score"] / r["dim"]
    raise ValueError(metric)


def selection(data, metric, cut):
    r = data["R"]
    return r[values(r, metric) <= cut]


def best(r):
    # Highest truth probability, then smallest fit chi2/dimension, then index.
    matched = r[(r["prob"] > 0.5) & (r["id"] != 0)]
    ordered = np.lexsort(
        (matched["index"], matched["chi2"] / matched["dim"], -matched["prob"])
    )
    ranked = matched[ordered]
    _, indices = np.unique(ranked[["run", "event", "id"]], return_index=True)
    chosen = ranked[indices]
    return dict(zip(keys(chosen), chosen))


def counts(data, metric, cut):
    r = selection(data, metric, cut)
    m = best(r)
    truth = set(keys(data["P"]))
    assert set(m) <= truth
    accepted = r[np.abs(r["eta"]) < 4]
    fake = (~np.isfinite(accepted["prob"])) | (accepted["prob"] < 0.5)
    out = dict(
        events=len(data["E"]),
        truth=len(truth),
        matched=len(m),
        tracks=len(accepted),
        fakes=int(fake.sum()),
    )
    out.update(
        efficiency=len(m) / len(truth),
        fake_rate=int(fake.sum()) / len(accepted),
        duplicates=int(sum((r["prob"] > 0.5) & (r["id"] != 0)) - len(m)),
    )
    return out


def threshold(data, metric, target):
    r = selection(data, "none", 0)
    v = values(r, metric)
    match = (r["prob"] > 0.5) & (r["id"] != 0) & np.isfinite(v)
    order = np.argsort(v[match])
    ranked = r[match][order]
    _, indices = np.unique(ranked[["run", "event", "id"]], return_index=True)
    minimal = v[match][order][indices]
    if len(minimal) < target:
        return None
    return float(np.partition(minimal, target - 1)[target - 1])


def paired(reference, other, events):
    delta = np.array([other.get(k, 0) - reference.get(k, 0) for k in events])
    return dict(
        change=float(delta.sum()), se=float(delta.std(ddof=1) * np.sqrt(len(delta)))
    )


def event_counts(data, metric, cut):
    r = selection(data, metric, cut)
    m = best(r)
    out = {tuple(map(int, (e["run"], e["event"]))): [0, 0, 0] for e in data["E"]}
    for run, ev, _ in m:
        out[run, ev][0] += 1
    for t in r:
        if abs(t["eta"]) >= 4:
            continue
        a = out[int(t["run"]), int(t["event"])]
        a[2] += 1
        a[1] += not np.isfinite(t["prob"]) or t["prob"] < 0.5
    return out


def resolutions(data, metric, cut, common=None):
    b = best(selection(data, metric, cut))
    if common is not None:
        b = {k: v for k, v in b.items() if k in common}
    out = {}
    for x in ["d0res", "z0res", "qptres"]:
        v = np.array([t[x] for t in b.values()])
        v = v[np.isfinite(v)]
        if len(v):
            q = np.quantile(v, [0.025, 0.15865, 0.5, 0.84135, 0.975])
            out[x] = dict(
                n=len(v),
                median=float(q[2]),
                width68=float((q[3] - q[1]) / 2),
                width95=float((q[4] - q[0]) / 2),
            )
    return out


def check_same(data):
    first = next(iter(data.values()))["P"]
    for name, d in data.items():
        assert np.array_equal(first, d["P"]), f"Truth denominator mismatch: {name}"
        assert np.all(np.isfinite(d["R"]["score"])), name
        assert np.all(d["R"]["dim"] > 0), name
        assert np.array_equal(
            d["R"]["dim"], d["R"]["ndf"]
        ), f"State score dimension/copy mismatch: {name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["tune", "evaluate"])
    ap.add_argument("directory", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--plan", type=Path)
    args = ap.parse_args()
    data = {
        p.name: load(p)
        for p in sorted(args.directory.iterdir())
        if (p / "rows.tsv").exists() or (p / "rows.npz").exists()
    }
    check_same(data)
    if args.action == "tune":
        ref = counts(data["tail5"], "none", 0)["matched"]
        report = dict(
            reference="tail5",
            reference_matches=ref,
            events=[list(map(int, (e["run"], e["event"]))) for e in data["tail5"]["E"]],
            inclusive={n: counts(d, "none", 0) for n, d in data.items()},
            choices={},
        )
        for retention in [0.98, 0.985, 0.99, 0.995, 0.998, 1.0]:
            target = int(np.ceil(retention * ref))
            groups = {}
            for family in ["core", "previous", "new"]:
                candidates = []
                for name, d in data.items():
                    if name.startswith("core") != (family == "core"):
                        continue
                    for metric in (
                        ["score/dim"] if family == "new" else ["chi2", "chi2/dim"]
                    ):
                        cut = threshold(d, metric, target)
                        if cut is None:
                            continue
                        candidates.append(
                            dict(
                                variant=name,
                                metric=metric,
                                cut=cut,
                                training=counts(d, metric, cut),
                            )
                        )
                if candidates:
                    groups[family] = min(
                        candidates,
                        key=lambda c: (
                            c["training"]["fakes"],
                            c["training"]["matched"] - target,
                            c["training"]["tracks"],
                        ),
                    )
            report["choices"][str(retention)] = dict(target=target, groups=groups)
    else:
        plan = json.loads(args.plan.read_text())
        train_events = set(map(tuple, plan["events"]))
        events = [
            tuple(map(int, (e["run"], e["event"])))
            for e in next(iter(data.values()))["E"]
        ]
        assert not train_events.intersection(events), "Tuning/validation overlap"
        report = dict(
            events=len(events),
            inclusive={n: counts(d, "none", 0) for n, d in data.items()},
            points={},
        )
        for retention, point in plan["choices"].items():
            groups = {}
            common = None
            for family, c in point["groups"].items():
                if c["variant"] not in data:
                    continue
                d = data[c["variant"]]
                k = set(best(selection(d, c["metric"], c["cut"])))
                common = k if common is None else common & k
                groups[family] = dict(
                    **c,
                    validation=counts(d, c["metric"], c["cut"]),
                    resolutions=resolutions(d, c["metric"], c["cut"]),
                )
            evstats = {}
            for family, c in groups.items():
                d = data[c["variant"]]
                c["common_resolutions"] = resolutions(d, c["metric"], c["cut"], common)
                evstats[family] = event_counts(d, c["metric"], c["cut"])
            comparisons = {}
            for family in ["core", "previous"]:
                if family not in groups or "new" not in groups:
                    continue
                comparisons["new-" + family] = {
                    name: paired(
                        {e: v[j] for e, v in evstats[family].items()},
                        {e: v[j] for e, v in evstats["new"].items()},
                        events,
                    )
                    for j, name in enumerate(["matched", "fakes", "tracks"])
                }
                ref = np.array([evstats[family][e] for e in events], dtype=float)
                new = np.array([evstats["new"][e] for e in events], dtype=float)
                truth_per_event = next(iter(data.values()))["E"]["particles"].astype(
                    float
                )
                delta_eff = (new[:, 0].sum() - ref[:, 0].sum()) / truth_per_event.sum()
                eff_influence = (
                    new[:, 0] - ref[:, 0] - delta_eff * truth_per_event
                ) / truth_per_event.sum()
                ref_fake = ref[:, 1].sum() / ref[:, 2].sum()
                new_fake = new[:, 1].sum() / new[:, 2].sum()
                fake_influence = (new[:, 1] - new_fake * new[:, 2]) / new[
                    :, 2
                ].sum() - (ref[:, 1] - ref_fake * ref[:, 2]) / ref[:, 2].sum()
                factor = len(events) / (len(events) - 1)
                comparisons["new-" + family]["rates"] = dict(
                    efficiency_change_pp=100 * delta_eff,
                    efficiency_se_pp=100
                    * float(np.sqrt(factor * (eff_influence**2).sum())),
                    fake_rate_change_pp=100 * (new_fake - ref_fake),
                    fake_rate_se_pp=100
                    * float(np.sqrt(factor * (fake_influence**2).sum())),
                )
            report["points"][retention] = dict(
                groups=groups, common_truth=len(common or []), paired=comparisons
            )
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
