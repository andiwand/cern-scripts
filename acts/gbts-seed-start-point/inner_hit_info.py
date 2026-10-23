# Linearised circle y = a + b r + k r^2 / 2, no scattering (high-pT limit).
# sigma(k) with and without the innermost pixel hit.
import numpy as np
pix = [34, 99, 160, 228, 291]; strip = [405, 562, 762, 1000]
def sk(radii, sig):
    r = np.asarray(radii, float); H = np.stack([np.ones_like(r), r, r * r / 2], 1)
    return np.sqrt(np.linalg.inv(H.T @ np.diag(1 / np.asarray(sig) ** 2) @ H)[2, 2])
for label, radii, sig in [("pixel", pix, [14] * 5), ("pixel+strip", pix + strip, [14] * 5 + [22] * 4)]:
    print(f"{label}: sigma(k) without innermost / with = {sk(radii[1:], sig[1:]) / sk(radii, sig):.3f}")
