# Noise-free circle tracks through the GBTS filter (transverse block only),
# with the #6254 conversion at the innermost node. Shows model bias only.
import numpy as np

SIGMA_X, SIGMA_MS, RADLEN, MAXCURV = 0.08, 0.016, 0.025, 1e-3
VAR0 = (0.25, 0.001, 0.001)

def hits(R, radii, phi0=0.3):
    # circle through the origin, start direction phi0, bending left
    t = 2 * np.arcsin(np.asarray(radii) / (2 * R))
    x, y = R * np.sin(t), R * (1 - np.cos(t))
    c, s = np.cos(phi0), np.sin(phi0)
    return np.stack([c * x - s * y, s * x + c * y], 1), phi0 + t  # pos, true phi

def gbts(pts):
    # pts ordered outer -> inner, head edge = pts[0] (n2) -> pts[1] (n1)
    d = pts[1] - pts[0]; L = np.hypot(*d); c, s = d / L
    refX = pts[0] @ [c, s]
    x = np.array([-pts[0][0] * s + pts[0][1] * c, 0., 0.])
    C = np.diag(VAR0).astype(float)
    for p in pts[1:]:
        C[1, 1] += RADLEN * (SIGMA_MS * abs(x[2]) / MAXCURV) ** 2  # barrel, eta 0
        X = p @ [c, s]; A = X - refX; B = 0.5 * A * A
        F = np.array([[1, A, B], [0, 1, A], [0, 0, 1]])
        x = F @ x; C = F @ C @ F.T
        m = -p[0] * s + p[1] * c
        K = C[:, 0] / (C[0, 0] + SIGMA_X ** 2)
        x = x + K * (m - x[0]); C = C - np.outer(K, C[0]); refX = X
    slope2 = 1 + x[1] ** 2
    curv = x[2] / slope2 ** 1.5
    phi = np.arctan2(-s - c * x[1], -c + s * x[1])
    return curv, phi

pix = [34, 99, 160, 228, 291]          # ITk-like pixel barrel radii, mm
strip = [405, 562, 762, 1000]          # ITk-like strip barrel radii, mm
for label, radii in [("pixel", pix), ("pixel+strip", pix + strip)]:
    print(label)
    for pT in [0.6, 0.9, 2, 10]:
        R = pT / (0.3 * 2.0) * 1000     # mm in 2 T
        if 2 * R < radii[-1]:
            continue
        pos, phis = hits(R, radii)
        curv, phi = gbts(pos[::-1])
        print(f"  pT {pT:5.1f} GeV  curvature/true {abs(curv) * R:.4f}  "
              f"phi bias {1e3 * (phi - phis[0]):+.3f} mrad")
