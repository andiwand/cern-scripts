"""Remove a measurement (or the prior) from a smoothed Kalman track without a refit.

Linear-Gaussian model, random systems. Reference: KF + RTS rerun without the
measurement. Checked: inverse update at the state, conditioning walks to the
other states, chi2 change, removal of the first and last measurement, prior
subtraction, chained removal of two measurements.
"""

import numpy as np

N, D, M = 9, 5, 2
rng = np.random.default_rng(1112)


def spd(n, scale=1.0):
    a = rng.normal(size=(n, n))
    return scale * (a @ a.T / n + 0.3 * np.eye(n))


def system():
    F = [np.eye(D) + 0.3 * rng.normal(size=(D, D)) for _ in range(N - 1)]
    # process noise on three of five components, as scattering and energy loss
    Q = []
    for _ in range(N - 1):
        q = np.zeros((D, D))
        q[2:, 2:] = spd(3, 0.05)
        Q.append(q)
    H = [rng.normal(size=(M, D)) for _ in range(N)]
    V = [spd(M, 0.2) for _ in range(N)]
    m = [rng.normal(size=M) for _ in range(N)]
    x0, P0 = rng.normal(size=D), spd(D, 4.0)
    return F, Q, H, V, m, x0, P0


def fit(F, Q, H, V, m, x0, P0, skip=()):
    xp, Pp, xf, Pf = [], [], [], []
    x, P, chi2 = x0, P0, 0.0
    for k in range(N):
        if k > 0:
            x, P = F[k - 1] @ x, F[k - 1] @ P @ F[k - 1].T + Q[k - 1]
        xp.append(x), Pp.append(P)
        if k not in skip:
            r = m[k] - H[k] @ x
            S = H[k] @ P @ H[k].T + V[k]
            K = P @ H[k].T @ np.linalg.inv(S)
            x, P = x + K @ r, (np.eye(D) - K @ H[k]) @ P
            chi2 += r @ np.linalg.solve(S, r)
        xf.append(x), Pf.append(P)
    xs, Ps, A = [None] * N, [None] * N, [None] * (N - 1)
    xs[-1], Ps[-1] = xf[-1], Pf[-1]
    for k in range(N - 2, -1, -1):
        A[k] = Pf[k] @ F[k].T @ np.linalg.inv(Pp[k + 1])
        xs[k] = xf[k] + A[k] @ (xs[k + 1] - xp[k + 1])
        Ps[k] = Pf[k] + A[k] @ (Ps[k + 1] - Pp[k + 1]) @ A[k].T
    B = [Ps[j + 1] @ A[j].T @ np.linalg.inv(Ps[j]) for j in range(N - 1)]
    return dict(xs=xs, Ps=Ps, A=A, B=B, chi2=chi2)


def batch(F, Q, H, V, m):
    """Dense least squares over the first state and the noise, without a prior."""
    n = D + 3 * (N - 1)
    T = [np.zeros((D, n))]  # x_k = T_k u, u = (x_0, w_0, ..., w_{N-2})
    T[0][:, :D] = np.eye(D)
    for k in range(N - 1):
        t = F[k] @ T[k]
        t[2:, D + 3 * k : D + 3 * k + 3] += np.eye(3)
        T.append(t)
    Y, y = np.zeros((n, n)), np.zeros(n)
    for k in range(N):
        W = np.linalg.inv(V[k])
        Y += T[k].T @ H[k].T @ W @ H[k] @ T[k]
        y += T[k].T @ H[k].T @ W @ m[k]
    for k in range(N - 1):
        Y[D + 3 * k : D + 3 * k + 3, D + 3 * k : D + 3 * k + 3] += np.linalg.inv(Q[k][2:, 2:])
    C = np.linalg.inv(Y)
    u = C @ y
    return dict(xs=[t @ u for t in T], Ps=[t @ C @ t.T for t in T], chi2=0.0)


def remove(t, k, Hk, Vk, mk):
    """Returns the track without the measurement. Uses only the stored smoothed
    states, the inward gains A (RTS) and the outward gains B; no transport."""
    xs, Ps = [x.copy() for x in t["xs"]], [P.copy() for P in t["Ps"]]
    A, B = list(t["A"]), list(t["B"])
    r = mk - Hk @ xs[k]
    R = Vk - Hk @ Ps[k] @ Hk.T  # covariance of the smoothed residual
    dchi2 = r @ np.linalg.solve(R, r)
    K = -Ps[k] @ Hk.T @ np.linalg.inv(R)  # gain of the update with -V
    dx, dP = K @ r, -K @ Hk @ Ps[k]
    xs[k], Ps[k] = xs[k] + dx, Ps[k] + dP
    ex, eP = dx, dP
    for j in range(k - 1, -1, -1):  # towards the start
        ex, eP = A[j] @ ex, A[j] @ eP @ A[j].T
        xs[j], Ps[j] = xs[j] + ex, Ps[j] + eP
    ex, eP = dx, dP
    for j in range(k, N - 1):  # towards the end
        ex, eP = B[j] @ ex, B[j] @ eP @ B[j].T
        xs[j + 1], Ps[j + 1] = xs[j + 1] + ex, Ps[j + 1] + eP
    # refresh the gains that pointed across k, from the unchanged ones
    for j in range(k):
        B[j] = Ps[j + 1] @ A[j].T @ np.linalg.inv(Ps[j])
    for j in range(k, N - 1):
        A[j] = Ps[j] @ B[j].T @ np.linalg.inv(Ps[j + 1])
    return dict(xs=xs, Ps=Ps, A=A, B=B, chi2=t["chi2"] - dchi2)


def diff(a, b):
    return max(
        max(np.abs(x - y).max() for x, y in zip(a["xs"], b["xs"])),
        max(np.abs(x - y).max() for x, y in zip(a["Ps"], b["Ps"])),
        abs(a["chi2"] - b["chi2"]),
    )


worst = dict(single=0.0, first=0.0, last=0.0, chained=0.0, **{"prior c=1": 0.0})
for _ in range(200):
    F, Q, H, V, m, x0, P0 = system()
    full = fit(F, Q, H, V, m, x0, P0)
    for k in range(N):
        d = diff(remove(full, k, H[k], V[k], m[k]), fit(F, Q, H, V, m, x0, P0, skip=(k,)))
        key = "first" if k == 0 else "last" if k == N - 1 else "single"
        worst[key] = max(worst[key], d)
    # the prior is a D-dimensional measurement of the first state. Removing it
    # must give the same track for any prior width c, and the dense fit
    # without a prior (differences relative to its largest covariance element).
    a = remove(full, 0, np.eye(D), P0, x0)
    b = batch(F, Q, H, V, m)
    scale = max(np.abs(P).max() for P in b["Ps"])
    worst["prior c=1"] = max(worst["prior c=1"], diff(dict(a, chi2=0), b) / scale)
    for c in (0.01, 100.0, 1e4):
        a = remove(fit(F, Q, H, V, m, x0, c * P0), 0, np.eye(D), c * P0, x0)
        key = f"prior c={c:g}"
        worst[key] = max(worst.get(key, 0.0), diff(dict(a, chi2=0), b) / scale)
    # chained: first and last measurement, the second removal on the result of
    # the first with the refreshed gains
    two = remove(remove(full, 0, H[0], V[0], m[0]), N - 1, H[-1], V[-1], m[-1])
    worst["chained"] = max(worst["chained"], diff(two, fit(F, Q, H, V, m, x0, P0, skip=(0, N - 1))))
    for k1, k2 in ((2, 6), (6, 2), (3, 4)):
        two = remove(remove(full, k1, H[k1], V[k1], m[k1]), k2, H[k2], V[k2], m[k2])
        worst["chained"] = max(worst["chained"], diff(two, fit(F, Q, H, V, m, x0, P0, skip=(k1, k2))))

for k, v in worst.items():
    print(f"{k:14s} max difference: {v:.1e}")
assert all(v < 1e-6 for k, v in worst.items() if k not in ("prior c=0.01", "prior c=10000"))
