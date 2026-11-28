import concurrent.futures
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1]).resolve()
root.mkdir(parents=True, exist_ok=True)
cases = []
for mat in ["Fe", "lAr"]:
    for p in [4, 10, 100]:
        for mode in ["constant", "ion", "full"]:
            cases.append((mat, p, 1000, 10, mode, 1, 57391))
    for length in [10, 100]:
        cases.append((mat, 10, length, 1, "constant", 1, 57391))
for step in [1, 100]:
    cases.append(("Fe", 10, 1000, step, "constant", 1, 57391))
cases += [
    ("Fe", 10, 1000, 10, "msc", 1, 57391),
    ("Fe", 4, 1000, 10, "ioncsda", 1e9, 57391),
]
for mat in ["Fe", "lAr"]:
    for p in [4, 10, 100]:
        cases.append((mat, p, 1000, 10, "constant_uncut", 1e9, 82371))
for p in [4, 10, 100]:
    for step in [1, 1e9]:
        cases.append(("Fe", p, 1000, step, "full", 1, 82371))
cases += [
    ("lAr", 10, 1000, 1e9, "full", 1, 82371),
    ("Fe", 10, 1000, 1, "constant_uncut", 1e9, 82371),
]
for mat, p in [("Fe", 100), ("lAr", 100), ("Fe", 10)]:
    cases.append((mat, p, 1000, 10, "constant_all", 1e9, 82371))


def run(case):
    mat, p, length, step, mode, cut, seed = case
    name = f"{mat}_{p}_{length}_{step:g}_{mode}"
    with (root / (name + ".log")).open("w") as log:
        subprocess.run(
            [
                str(root / "build/scattering"),
                mat,
                str(p),
                str(length),
                str(step),
                mode,
                "150000",
                str(seed),
                str(cut),
                str(root / (name + ".bin")),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    print(name, flush=True)


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(run, cases))
# Small independent diagnostics of the actual converted cuts.
for mat, mode, suffix in [
    ("Fe", "constant_uncut", ""),
    ("lAr", "constant_uncut", "_lar"),
    ("Fe", "constant_all", "_all"),
]:
    with (root / f"cutcheck{suffix}.log").open("w") as log:
        subprocess.run(
            [
                str(root / "build/scattering"),
                mat,
                "100",
                "1000",
                "10",
                mode,
                "1000",
                "123",
                "1e9",
                str(root / f"cutcheck{suffix}.bin"),
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
