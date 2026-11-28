"""Bounded, training-selected hole/outlier scan; all pT selections unchanged."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

import numpy as np
from analyze import check_same, load
from nn_analyze import counts

SCRIPTS = Path(__file__).resolve().parent


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def design(root):
    variants = {}
    for family, lower, upper, uppers in [
        ("core", 10, 14, [10, 14, 20]),
        ("tail", 5, 7, [5, 7, 10]),
    ]:
        points = [(u, h, o) for u in uppers for h, o in [(1, 1), (2, 1), (1, 2)]]
        points += [(upper, h, o) for h, o in [(0, 1), (1, 0), (2, 2)]]
        for u, h, o in points:
            if (u, h, o) == (upper, 1, 1):
                continue  # Existing core10/tail5 are the exact anchors.
            variants[f"{family}{lower}u{u}h{h}o{o}"] = dict(
                tail=family == "tail",
                measurement_sigma=lower,
                outlier_sigma=u,
                max_holes=h,
                max_outliers=o,
            )
    assert len(variants) == 22
    return dict(
        method="Symmetric local scan around original main-point nominal/tail gates; not an exhaustive scan at every measurement gate",
        variants=variants,
        training_events=200,
        validation_events=800,
        validation_skip=200,
        targets="All six original raw training-match targets; main target 0.995",
        selection="Independent training minimization of fakes at fixed matched count; nominal/previous chi2 or chi2/dim, new score/dim",
        fixed="All pT cuts, truth/fake definitions, NN pre-calibration, seeds, mixture, shared-hit policy, per-subdetector limits and combined-count policy unchanged",
        caveat="Existing evaluation events have been inspected; exploratory, not fresh confirmation",
        original_plan_sha256=sha(root.parent / "training.json"),
        baseline_plan_sha256=sha(root.parent / "nn-extended/training.json"),
    )


def initialize(root):
    root.mkdir()
    (root / "training").mkdir()
    plan = design(root)
    write(root / "design.json", plan)
    for directory in sorted((root.parent / "nn-extended/training").iterdir()):
        if directory.is_dir():
            (root / "training" / directory.name).symlink_to(directory.resolve())
    return plan


def audit_run(path, variant, events, reference):
    assert (path / "exit-code").read_text().strip() == "0", path
    d = load(path)
    assert len(d["E"]) == events
    check_same({"reference": reference, variant: d})
    assert np.array_equal(d["E"][["run", "event"]], reference["E"][["run", "event"]])
    match = re.fullmatch(r"(core|tail)(\d+)u(\d+)h(\d+)o(\d+)", variant)
    family, lower, upper, holes, outliers = match.groups()
    log = (path / "log.RAWtoALL").read_text()
    for key, value in [
        ("Xi2maxSigma", lower),
        ("Xi2maxNoAddSigma", upper),
        ("maxHoles", holes),
        ("maxOutliers", outliers),
    ]:
        expected = rf"Tracking.ITkActsPass.{key}\s+: \[{value}(?:\.0)?\]"
        assert re.search(expected, log), (variant, key)
    assert re.search(r"Tracking.ITkActsPass.maxHolesAndOutliers\s+: \[\]", log)

    def pass_flags(text):
        return dict(re.findall(r"Tracking.ITkActsPass\.(\w+)\s+: ([^\n]+)", text))

    actual = pass_flags(log)
    original = pass_flags((reference_path / "log.RAWtoALL").read_text())
    changed = {"Xi2maxSigma", "Xi2maxNoAddSigma", "maxHoles", "maxOutliers"}
    assert actual.keys() == original.keys()
    assert {k: v for k, v in actual.items() if k not in changed} == {
        k: v for k, v in original.items() if k not in changed
    }, "Unexpected tracking-pass change, including pT"
    assert sha(path / "nn_native_config.py") == sha(
        reference_path / "nn_native_config.py"
    )
    assert (path / "library-sha256.txt").read_text() == (
        reference_path / "library-sha256.txt"
    ).read_text()
    write(
        path / "scan-audit.json",
        dict(
            events=events,
            checks="Exits, event identities, truth, dimensions, active cuts and NN library agree",
            inclusive=counts(d, "none", 0),
        ),
    )


def run_batch(root, stage, variants, events, skip, parallel):
    global reference_path
    reference_path = root.parent / "nn-extended" / stage / "core10"
    reference = load(reference_path)
    stop = root / "STOP"

    def run(variant):
        path = root / stage / variant
        if path.exists():
            assert (
                path / "scan-audit.json"
            ).exists(), f"Incomplete previous run: {path}"
            return
        assert not stop.exists(), "Scan stopped; inspect STOP"
        assert (
            shutil.disk_usage(root).free > 12 * 2**30
        ), "Less than 12 GiB free before run"
        with (root / stage / (variant + ".driver.log")).open("x") as stream:
            process = subprocess.Popen(
                [
                    "bash",
                    str(SCRIPTS / "run_hole_scan.sh"),
                    str(path),
                    variant,
                    str(events),
                    str(skip),
                    "4" if stage == "training" else "8",
                    "1",
                ],
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            while process.poll() is None:
                if shutil.disk_usage(root).free < 8 * 2**30:
                    import os, signal

                    stop.write_text("Disk reserve reached; reconstruction stopped\n")
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait()
                    raise RuntimeError("Disk reserve reached")
                time.sleep(5)
            assert process.returncode == 0, (variant, process.returncode)
        audit_run(path, variant, events, reference)
        if stage == "training":
            aod = path / "myAOD.pool.root"
            write(
                path / "aod-cleanup.json",
                dict(
                    path=str(aod),
                    bytes=aod.stat().st_size,
                    sha256=sha(aod),
                    reason="Training export and audit complete; preserve rows, caches, config and logs",
                ),
            )
            aod.unlink()
        print(stage, variant, "passed", flush=True)

    def guarded_run(variant):
        try:
            run(variant)
        except BaseException:
            if not stop.exists():
                stop.write_text(f"Failure in {stage}/{variant}; inspect logs\n")
            raise

    with ThreadPoolExecutor(max_workers=parallel) as pool:
        list(pool.map(guarded_run, variants))


def freeze(root):
    plan_path = root / "training.json"
    plan = json.loads(plan_path.read_text())
    data = {p.name: load(p) for p in (root / "training").iterdir() if p.is_dir()}
    check_same(data)
    assert len(plan["events"]) == 200
    for p in (root / "training").iterdir():
        if p.is_dir():
            assert (p / "exit-code").read_text().strip() == "0"
    for point in plan["choices"].values():
        assert set(point["groups"]) == {"core", "previous", "new"}
        for c in point["groups"].values():
            assert counts(data[c["variant"]], c["metric"], c["cut"]) == c["training"]
            assert c["training"]["matched"] >= point["target"]
    selected = sorted(
        {c["variant"] for p in plan["choices"].values() for c in p["groups"].values()}
    )
    assert not (root / "validation").exists()
    write(
        root / "frozen-plan.json",
        dict(
            training_sha256=sha(plan_path),
            design_sha256=sha(root / "design.json"),
            validation_variants=selected,
            checks="All training exits, shared truth and independent recomputed choices pass; no scan validation before freeze",
        ),
    )
    (root / "validation").mkdir()
    for v in selected:
        old = root.parent / "nn-extended/validation" / v
        if old.exists():
            (root / "validation" / v).symlink_to(old.resolve())
    return selected


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        manifest = initialize(root)
        run_batch(root, "training", sorted(manifest["variants"]), 200, 0, 4)
        with (root / "tuning.log").open("w") as log:
            subprocess.run(
                [
                    "python",
                    str(SCRIPTS / "nn_analyze.py"),
                    "tune",
                    str(root / "training"),
                    str(root / "training.json"),
                    "--reference-plan",
                    str(root.parent / "training.json"),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        chosen = freeze(root)
        run_batch(
            root,
            "validation",
            [v for v in chosen if not (root / "validation" / v).exists()],
            800,
            200,
            2,
        )
        with (root / "evaluation.log").open("w") as log:
            subprocess.run(
                [
                    "python",
                    str(SCRIPTS / "nn_analyze.py"),
                    "evaluate",
                    str(root / "validation"),
                    str(root / "validation.json"),
                    "--plan",
                    str(root / "training.json"),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
    except BaseException:
        if root.exists():
            (root / "exit-code").write_text("1\n")
        raise
    (root / "exit-code").write_text("0\n")
