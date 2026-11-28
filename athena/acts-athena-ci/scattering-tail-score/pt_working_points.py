"""Exploratory reconstructed-pT slices with frozen quality cuts; no retuning."""

from pathlib import Path
import json
import sys
import numpy as np
from analyze import load, check_same, selection

root = Path(sys.argv[1])
plan = json.loads((root / "training.json").read_text())["choices"]["0.995"]["groups"]
data = {c["variant"]: load(root / "validation" / c["variant"]) for c in plan.values()}
raw_root = Path(sys.argv[2]) if len(sys.argv) > 2 else None
if raw_root:
    raw_choice = json.loads((raw_root / "training.json").read_text())["choices"][
        "0.995"
    ]["groups"]["core"]
    data["raw-core"] = load(raw_root / "validation" / raw_choice["variant"])
check_same(data)
first = next(iter(data.values()))
events = first["E"][["run", "event"]]
truth = first["P"]
truth_event = np.searchsorted(events, truth[["run", "event"]])
rows = {
    f: selection(data[c["variant"]], c["metric"], c["cut"]) for f, c in plan.items()
}
if raw_root:
    rows["raw-core"] = selection(
        data["raw-core"], raw_choice["metric"], raw_choice["cut"]
    )
row_event = {f: np.searchsorted(events, r[["run", "event"]]) for f, r in rows.items()}


def rates(ref, new, nt, N):
    delta = (new[:, 0].sum() - ref[:, 0].sum()) / nt.sum()
    ei = (new[:, 0] - ref[:, 0] - delta * nt) / nt.sum()
    rf = ref[:, 1].sum() / ref[:, 2].sum()
    nf = new[:, 1].sum() / new[:, 2].sum()
    fi = (new[:, 1] - nf * new[:, 2]) / new[:, 2].sum() - (
        ref[:, 1] - rf * ref[:, 2]
    ) / ref[:, 2].sum()
    return dict(
        efficiency_change_pp=100 * delta,
        efficiency_se_pp=100 * float(np.sqrt(N / (N - 1) * np.sum(ei**2))),
        fake_rate_change_pp=100 * (nf - rf),
        fake_rate_se_pp=100 * float(np.sqrt(N / (N - 1) * np.sum(fi**2))),
    )


N = len(events)
out = {}
for true_pt in [1.0, 2.0, 5.0]:
    p = truth[truth["pt"] > true_pt]
    nt = np.bincount(truth_event[truth["pt"] > true_pt], minlength=N).astype(float)
    for reco_pt in [0.0, 0.5, 1.0, 2.0]:
        stats = {}
        counts = {}
        for family, r in rows.items():
            use = r["pt"] >= reco_pt
            m = np.unique(
                r[use & (r["prob"] > 0.5) & (r["id"] != 0)][["run", "event", "id"]]
            )
            m = np.intersect1d(m, p[["run", "event", "id"]], assume_unique=True)
            accepted = use & (np.abs(r["eta"]) < 4)
            fake = accepted & ((r["prob"] < 0.5) | ~np.isfinite(r["prob"]))
            matched = np.bincount(
                np.searchsorted(events, m[["run", "event"]]), minlength=N
            )
            nf = np.bincount(row_event[family][fake], minlength=N)
            nr = np.bincount(row_event[family][accepted], minlength=N)
            stats[family] = np.column_stack((matched, nf, nr)).astype(float)
            counts[family] = dict(
                truth=len(p),
                matched=len(m),
                fakes=int(nf.sum()),
                tracks=int(nr.sum()),
                efficiency=len(m) / len(p),
                fake_rate=float(nf.sum() / nr.sum()),
            )
        paired = rates(stats["core"], stats["new"], nt, N)
        out[f"truth>{true_pt:g},reco>={reco_pt:g}"] = dict(
            truth_pt_min=true_pt, reco_pt_min=reco_pt, counts=counts, paired=paired
        )
        if raw_root:
            out[f"truth>{true_pt:g},reco>={reco_pt:g}"]["paired_raw"] = rates(
                stats["raw-core"], stats["new"], nt, N
            )
reference = json.loads((root / "validation.json").read_text())["points"]["0.995"][
    "groups"
]
if raw_root:
    reference["raw-core"] = json.loads((raw_root / "validation.json").read_text())[
        "points"
    ]["0.995"]["groups"]["core"]
for family, c in out["truth>1,reco>=0"]["counts"].items():
    assert all(reference[family]["validation"][k] == v for k, v in c.items()), family
if (root / "pt-working-points.json").exists():
    previous = json.loads((root / "pt-working-points.json").read_text())["points"]
    for point, old in previous.items():
        assert out[point]["paired"] == old["paired"]
        for family, old_count in old["counts"].items():
            assert out[point]["counts"][family] == old_count
result = dict(
    method="Same frozen .995 quality selections; reconstructed-pT cuts applied to tracks for both efficiency and fake counting. No tuning to these slices; exploratory after inspection.",
    points=out,
)
(root / "pt-working-points.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(out["truth>1,reco>=1"], indent=2))
