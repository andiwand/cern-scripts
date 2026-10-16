"""Partition inclusive hits by annihilation ancestry and G4 creation location."""

import argparse, csv, gzip, json, math
from pathlib import Path
from collections import Counter

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--work", type=Path, required=True)
a = p.parse_args()
s = Path.home() / "cern/scripts/acts"
ids = ["pv", "sv", "part", "gen", "subpart"]


def identity(r, prefix="particle_id_"):
    return tuple(r[prefix + k] for k in ids)


def rows(f):
    with gzip.open(f, "rt") if f.suffix == ".gz" else f.open() as stream:
        yield from csv.DictReader(stream)


def locate(root, e, name):
    p = root / f"event{e:09d}-{name}.csv"
    return p if p.exists() else p.with_suffix(".csv.gz")


def analyse(root):
    events = []
    for e in range(3):
        truth = {}
        for r in rows(locate(root, e, "particles_simulated")):
            momentum = math.sqrt(sum(float(r[k]) ** 2 for k in ["px", "py", "pz"]))
            mass = float(r["m"])
            ke = (
                momentum * momentum / (math.hypot(momentum, mass) + mass)
                if momentum or mass
                else 0
            )
            truth[identity(r)] = (
                r["particle_type"],
                r["process"],
                identity(r, "parent_id_"),
                ke * 1000,
            )

        cache = {}

        def origin(pid):
            path = []
            key = pid
            while key in truth and key not in cache:
                assert key not in path
                path.append(key)
                pdg, proc, parent = truth[key][:3]
                par = truth.get(parent)
                if pdg == "22" and proc == "6" and par and par[0] == "-11":
                    label = "annihilation"
                    break
                if int(key[3]) == 0:
                    label = "other lineage"
                    break
                key = parent
            else:
                label = cache.get(key, "unknown ancestry")
            for key in path:
                cache[key] = label
            return label

        counts = Counter()
        photons = Counter()
        flow = Counter()
        pairs = {}
        carriers = set()
        for pid, t in truth.items():
            if t[0] == "22" and t[1] == "6" and truth.get(t[2], ("",))[0] == "-11":
                photons["retained annihilation photons"] += 1
                pairs.setdefault(t[2], []).append(t[3])
            if origin(pid) == "annihilation":
                flow[
                    f'particles:{t[1]}:{t[0]}:{"below 100 keV" if t[3]<.1 else "at least 100 keV"}'
                ] += 1
            if t[1] == "5":
                parent = truth.get(t[2])
                group = (
                    "electron or positron"
                    if parent and abs(int(parent[0])) == 11
                    else "other charged"
                )
                flow[
                    f'ionisation particles:{group}:{"below 100 keV" if t[3]<.1 else "at least 100 keV"}'
                ] += 1
                if t[3] >= 2:
                    flow[f"ionisation particles:{group}:at least 2 MeV"] += 1

        def photon_root(pid):
            visited = set()
            while pid in truth:
                assert pid not in visited
                visited.add(pid)
                pdg, proc, parent, _ = truth[pid]
                if pdg != "22":
                    return "unknown"
                if int(pid[3]) == 0:
                    return "primary"
                if proc != "6":
                    return {"1": "Decay", "3": "eBrem", "4": "nuclear"}.get(
                        proc, "other"
                    )
                if truth.get(parent, ("",))[0] == "-11":
                    return "annihil"
                pid = parent
            return "unknown"

        for energies in pairs.values():
            if len(energies) != 2:
                flow["annihilation pairs:incomplete"] += 1
            else:
                flow[
                    "annihilation pairs:"
                    + (
                        "at rest"
                        if abs(sum(energies) - 1.0219979) < 0.001
                        else "in flight"
                    )
                ] += 1
        for h in rows(locate(root, e, "hits")):
            pid = identity(h)
            if int(pid[3]) == 0:
                continue
            proc = truth[pid][1]
            label = origin(pid)
            if proc == "6" and root.name == "current-0":
                flow["Compton hits by photon source:" + photon_root(truth[pid][2])] += 1
            if proc == "5":
                parent = truth.get(truth[pid][2])
                group = (
                    "electron or positron"
                    if parent and abs(int(parent[0])) == 11
                    else "other charged"
                )
                flow[f"ionisation hits:{group}:all"] += 1
                if truth[pid][3] >= 2:
                    flow[f"ionisation hits:{group}:at least 2 MeV"] += 1
            if label == "annihilation" and pid not in carriers:
                t = truth[pid]
                flow[
                    f'hit carriers:{t[1]}:{t[0]}:{"below 100 keV" if t[3]<.1 else "at least 100 keV"}'
                ] += 1
                carriers.add(pid)
            for scope in [
                "ID",
                "pixel" if int(h["geometry_id"]) >> 56 in [16, 17, 18] else "strip",
            ]:
                counts[f"{scope}:{label}:{proc}"] += 1
        events.append(dict(hits=dict(counts), truth=dict(photons), flow=dict(flow)))
        print(root.name, e, dict(photons), flush=True)

    def mean(key):
        return {
            k: sum(ev[key].get(k, 0) for ev in events) / 3
            for k in set().union(*(ev[key] for ev in events))
        }

    return dict(
        events=events,
        mean_hits=mean("hits"),
        mean_truth=mean("truth"),
        mean_flow=mean("flow"),
    )


d = {
    name: analyse(root)
    for name, root in [
        ("Current", a.work / "current-0"),
        ("Geant4", s / "fatras-soft-secondaries/results/2026-10-15/geant4"),
    ]
}
obs = s / "fatras-material-locality/results/2026-10-16/geant4-observed/observer.tsv.gz"
counts = Counter()
compton = Counter()
with gzip.open(obs, "rt") as stream:
    for r in csv.DictReader(stream, delimiter="\t"):
        if r["creator"] == "primary":
            continue
        site = (
            "sensor birth" if "ActsSensitive#" in r["birth_volume"] else "other birth"
        )
        counts[
            f"{r['creator']}:{site}:{'below 100 keV' if float(r['birth_ke_MeV'])<.1 else 'at least 100 keV'}"
        ] += 1
        if r["creator"] == "compt":
            compton[f"{r['parent_creator']}:{site}"] += 1
d["g4_observer"] = dict(
    process_location_energy={k: v / 3 for k, v in counts.items()},
    compton_parent_location={k: v / 3 for k, v in compton.items()},
    path=str(obs),
)
(a.work / "attribution.json").write_text(json.dumps(d, indent=2))
