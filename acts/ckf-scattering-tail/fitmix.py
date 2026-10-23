#!/usr/bin/env python3
"""Two-Gaussian approximation of the Fatras general mixture (semi-Gaussian
regime) for one projected angle, in units of the Highland width.

The table printed here is the one in Core/.../detail/ScatteringTail.hpp.
"""
import sys
from math import erfc, sqrt

import numpy as np

rng = np.random.default_rng(1)


def semigauss_params(t, Z=14.0, beta=1.0):
    N = t * 1.587e7 * Z ** (1 / 3) / beta**2 / (Z + 1) / np.log(287 / np.sqrt(Z))
    rho = 41000 / Z ** (2 / 3)
    b = rho / np.sqrt(N * (np.log(rho) - 0.5))
    n = Z**0.1 * np.log(N)
    var1 = (5.783e-4 * n + 3.803e-2) * n + 1.827e-1
    a = (((-4.590e-5 * n + 1.330e-3) * n - 1.355e-2) * n + 9.828e-2) * n + 2.822e-1
    eps = max((1 - var1) / (a * a * (np.log(b / a) - 0.5) - var1), 0)
    return a, b, var1, eps


def sample(t, n=2_000_000):
    a, b, var1, eps = semigauss_params(t)
    sig = 15.0 * np.sqrt(t)
    tail = rng.random(n) < eps
    u = rng.random(n)
    th = np.where(~tail, np.sqrt(var1) * np.sqrt(-2 * np.log(u)) * sig,
                  a * b * np.sqrt((1 - u) / (u * b * b + a * a)) * sig)
    return th * np.cos(rng.uniform(-np.pi, np.pi, n))


def highland(t):
    return 13.6 * np.sqrt(t) * (1 + 0.038 * np.log(t))


def em(x, iters=200):
    s1, s2, e = np.std(x) * 0.8, np.std(x) * 3, 0.05
    for _ in range(iters):
        l1 = (1 - e) * np.exp(-x * x / 2 / s1**2) / s1
        l2 = e * np.exp(-x * x / 2 / s2**2) / s2
        w = l2 / (l1 + l2)
        e = w.mean()
        s1 = np.sqrt(((1 - w) * x * x).sum() / (1 - w).sum())
        s2 = np.sqrt((w * x * x).sum() / w.sum())
    return e, s1, s2


ts = [0.003, 0.005, 0.01, 0.02, 0.04, 0.08]
eps, ks = [], []
print(" t/X0  lnT      eps    core/HL  tail/HL  frac>4HL sampled  fit")
for t in ts:
    x = sample(t)
    hl = highland(t)
    e, s1, s2 = em(x)
    f4 = (np.abs(x) > 4 * hl).mean()
    f4m = (1 - e) * erfc(4 * hl / s1 / sqrt(2)) + e * erfc(4 * hl / s2 / sqrt(2))
    print(f"{t:6.3f} {np.log(t):7.4f} {e:7.4f} {s1/hl:7.3f} {s2/hl:7.3f}   {f4:.4f}  {f4m:.4f}")
    eps.append(e)
    ks.append(s2 / hl)
    if t == 0.02:
        xn = x / hl
        bins = np.linspace(-15, 15, 301)
        xs = 0.5 * (bins[1:] + bins[:-1])
        c1, c2 = s1 / hl, s2 / hl
        fit = (1 - e) * np.exp(-xs**2 / 2 / c1**2) / c1 / sqrt(2 * np.pi) + e * np.exp(
            -xs**2 / 2 / c2**2) / c2 / sqrt(2 * np.pi)
        hlc = np.exp(-xs**2 / 2) / sqrt(2 * np.pi)
        keep = (xn, bins, fit, hlc)

if len(sys.argv) > 1:
    xn, bins, fit, hlc = keep
    np.savez(sys.argv[1], x=xn[:500_000], bins=bins, fit=fit, hl=hlc, t=0.02,
             ts=np.array(ts), eps=np.array(eps), k=np.array(ks))
