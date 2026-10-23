# sigma of the predicted r-phi position at layer 0 from the outer hits,
# GLS with correlated multiple scattering. Rough ITk-like barrel, eta 0.
import numpy as np
pix = [34, 99, 160, 228, 291]; strip = [405, 562, 762, 1000]
def theta0(p, x):  # Highland, rad
    return 0.0136 / p * np.sqrt(x) * (1 + 0.038 * np.log(x))
def sigma_y0(radii, sig, x0, p):
    r = np.asarray(radii, float); r0 = 34.0
    H = np.stack([np.ones_like(r), r - r0, (r - r0) ** 2 / 2], 1)
    V = np.diag((np.asarray(sig, float) * 1e-3) ** 2)  # um -> mm
    for rj, xj in zip(r, x0):  # scatter in layer j moves every outer hit
        d = np.clip(r - rj, 0, None)
        V += theta0(p, xj) ** 2 * np.outer(d, d)
    C = np.linalg.inv(H.T @ np.linalg.solve(V, H))
    return np.sqrt(C[0, 0]) * 1e3  # um
for p in [1, 10]:
    a = sigma_y0(pix[1:], [14] * 4, [0.02] * 4, p)
    b = sigma_y0(pix[1:] + strip, [14] * 4 + [22] * 4, [0.02] * 4 + [0.025] * 4, p)
    print(f"p {p:3d} GeV: pixel 1-4 {a:6.1f} um, pixel 1-4 + strips {b:6.1f} um")
