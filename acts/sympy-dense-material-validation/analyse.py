import pathlib, sys
import numpy as np
import pandas as pd
from comparison_common import robust_gauss_fit

root = pathlib.Path(sys.argv[1])


def width(x):
    return robust_gauss_fit(x)[0][1]


rows = []
for path in sorted(root.glob("*.bin")):
    if path.stat().st_size != 150000 * 12 * 8:
        continue
    parts = path.stem.split("_", 4)
    mat, p, L, h, mode = parts
    p, L, h = map(float, [p, L, h])
    if path.stat().st_size != 150000 * 12 * 8:
        continue
    data = np.fromfile(path).reshape(-1, 12)
    if len(data) != 150000:
        continue
    d = data[data[:, 0] == 2]
    X0 = {"Fe": 17.57493465097, "lAr": 140.0343868497}[mat]
    beta = p / np.hypot(p, 0.1056583755)
    x = L / X0
    theta = 0.0136 / (p * beta) * np.sqrt(x) * (1 + 0.038 * np.log(x / (beta * beta)))
    # Analytical cumulative Highland weighting, derivative of s (A+b log(s/L))^2.
    # <s>/L = 1/2+b/(2A)-b^2/(4A^2); <s²>/L² = 1/3+4b/(9A)-4b²/(27A²)
    A = 1 + 0.038 * np.log(x / beta**2)
    b = 0.038
    s1 = L * (0.5 + b / (2 * A) - b * b / (4 * A * A))
    s2 = L * L * (1 / 3 + 4 * b / (9 * A) - 4 * b * b / (27 * A * A))
    D = 1500 + L / 2
    screen = theta * np.sqrt(D * D - 2 * D * s1 + s2)
    row = dict(
        material=mat,
        p=p,
        L=L,
        h=h,
        mode=mode,
        n=len(d),
        acceptance=len(d) / len(data),
        pout_mean=d[:, 11].mean() / 1000,
        pout_std=d[:, 11].std() / 1000,
        path_mean=d[:, 10].mean(),
        theta_highland=theta,
        screen_highland=screen,
    )
    for key, idx, pred in [
        ("screen", 6, screen),
        ("angle", 3, theta),
        ("exit", 1, theta * np.sqrt(L * L - 2 * L * s1 + s2)),
    ]:
        z = d[:, idx]
        w = width(z)
        blocks = np.array([width(a) for a in np.array_split(z, 15)])
        row[key + "_core"] = w
        row[key + "_se"] = blocks.std(ddof=1) / np.sqrt(len(blocks))
        row[key + "_rms"] = z.std()
        row[key + "_q68"] = (
            np.quantile(z, 0.841344746) - np.quantile(z, 0.158655254)
        ) / 2
        row[key + "_ratio"] = w / pred
    row["lever_core"] = row["screen_core"] / row["angle_core"]
    row["lever_rms"] = row["screen_rms"] / row["angle_rms"]
    rows.append(row)
frame = pd.DataFrame(rows)
frame.to_csv(root / "summary.csv", index=False)
print(
    frame[
        [
            "material",
            "p",
            "L",
            "h",
            "mode",
            "n",
            "pout_mean",
            "screen_ratio",
            "angle_ratio",
            "lever_core",
            "path_mean",
        ]
    ].to_string(index=False)
)
