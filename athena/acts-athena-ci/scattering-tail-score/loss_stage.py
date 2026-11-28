"""Locate frozen-point truth losses before/at the final quality cut; no retuning."""

from pathlib import Path
import json
import sys
import numpy as np
from analyze import load, check_same, keys, selection

root = Path(sys.argv[1])
plan = json.loads((root / "training.json").read_text())["choices"]["0.995"]["groups"]
data = {c["variant"]: load(root / "validation" / c["variant"]) for c in plan.values()}
check_same(data)


def matched(rows):
    return set(keys(rows[(rows["prob"] > 0.5) & (rows["id"] != 0)]))


all_matches = {f: matched(data[c["variant"]]["R"]) for f, c in plan.items()}
selected = {
    f: matched(selection(data[c["variant"]], c["metric"], c["cut"]))
    for f, c in plan.items()
}
truth = next(iter(data.values()))["P"]
truth_keys = keys(truth)


def profile(ids):
    p = truth[np.array([k in ids for k in truth_keys])]

    def bins(field, edges, absolute=False):
        v = np.abs(p[field]) if absolute else p[field]
        return dict(edges=edges, counts=np.histogram(v, bins=edges)[0].tolist())

    return dict(
        n=len(p),
        pt=bins("pt", [1, 2, 5, 10, 1e9]),
        abs_eta=bins("eta", [0, 1, 2, 2.5, 3, 4], True),
        hard_scatter=int(p["hs"].sum()),
    )


lost = selected["core"] - selected["new"]
gained = selected["new"] - selected["core"]
loss_before = selected["core"] - all_matches["new"]
loss_cut = lost & all_matches["new"]
gain_finding = gained - all_matches["core"]
gain_quality = gained & all_matches["core"]
assert lost == loss_before | loss_cut and not loss_before & loss_cut
assert gained == gain_finding | gain_quality and not gain_finding & gain_quality
out = dict(
    point=0.995,
    definitions="Before final cut means absent from the saved post-finding/shared-hit-suppression AOD; it does not identify the precise internal loss stage.",
    inclusive_matches={f: len(v) for f, v in all_matches.items()},
    selected_matches={f: len(v) for f, v in selected.items()},
    cohorts={
        name: profile(ids)
        for name, ids in [
            ("lost", lost),
            ("lost_before_final_cut", loss_before),
            ("lost_by_final_cut", loss_cut),
            ("gained", gained),
            ("gained_in_finding", gain_finding),
            ("gained_through_quality_selection", gain_quality),
        ]
    },
)
(root / "loss-stage.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({k: v["n"] for k, v in out["cohorts"].items()}, indent=2))
