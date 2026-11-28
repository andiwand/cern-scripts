"""Persist the completed temporary scan, with useful new AODs backed up locally."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

source = Path("/dev/shm/astefl-hole-scan-work/hole-scan")
destination = Path(
    "/home/astefl/source/acts/acts-athena-ci/run/scattering-tail-score/hole-scan"
)
retained_aods = {"core10u10h2o1", "tail5u5h2o1"}


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 2**20), b""):
            digest.update(block)
    return digest.hexdigest()


assert (source / "exit-code").read_text().strip() == "0"
assert (source / "review-exit-code").read_text().strip() == "0"
assert not (source / "STOP").exists()
assert shutil.disk_usage(destination).free > 10 * 2**30
local_backups = json.loads((source / "local-validation-backup.json").read_text())
for name in ["exit-code", "review-exit-code", "STOP"]:
    old = destination / name
    assert sha(old) == sha(source / "disk-reserve-stop" / name), name
omitted = []
for path in sorted((source / "validation").glob("*/myAOD.pool.root")):
    if path.parent.is_symlink():
        continue
    if path.parent.name in retained_aods:
        assert (
            sha(path) == local_backups["files"][str(path.relative_to(source))]["sha256"]
        )
    omitted.append(
        dict(
            path=str(path.relative_to(source)),
            bytes=path.stat().st_size,
            sha256=sha(path),
        )
    )
omitted_tsv = [
    str(p.relative_to(source))
    for p in (source / "validation").glob("*/rows.tsv")
    if not p.parent.is_symlink()
]
for relative in omitted_tsv:
    cache = str(Path(relative).with_suffix(".npz"))
    assert sha(source / cache) == local_backups["files"][cache]["sha256"]
excluded = {item["path"] for item in omitted} | set(omitted_tsv)
command = ["rsync", "-a"]
command += ["--exclude=/" + name for name in sorted(excluded)]
subprocess.run(command + [str(source) + "/", str(destination) + "/"], check=True)
files = {}
for path in sorted(source.rglob("*")):
    relative = str(path.relative_to(source))
    target = destination / relative
    if path.is_symlink():
        assert target.is_symlink() and path.readlink() == target.readlink(), relative
        assert "/dev/shm/" not in str(target.resolve()), relative
    elif path.is_file() and relative not in excluded:
        expected = sha(path)
        assert target.is_file() and sha(target) == expected, relative
        files[relative] = dict(bytes=path.stat().st_size, sha256=expected)
assert sha(destination / "STOP") == sha(destination / "disk-reserve-stop/STOP")
(destination / "STOP").unlink()
review = dict(
    source=str(source),
    destination=str(destination),
    checks="All retained regular files match SHA256; symlinks resolve to persistent data; original disk-stop markers archived",
    files=files,
    omitted_aods=omitted,
    omitted_validation_tsv=omitted_tsv,
    local_backups=local_backups,
    retention="All analyzed arrays retained as NPZ; two useful AODs retained in verified local backup; other AODs regenerable from preserved RDO inputs",
)
(destination / "archive-review.json").write_text(json.dumps(review, indent=2) + "\n")
print(
    json.dumps(
        dict(
            files=len(files),
            bytes=sum(f["bytes"] for f in files.values()),
            omitted_aods=omitted,
        ),
        indent=2,
    )
)
