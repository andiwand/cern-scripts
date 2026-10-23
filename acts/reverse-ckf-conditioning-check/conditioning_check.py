import numpy as np

# Independent check: two linear-Gaussian arms share state 0. Compare
# segment smoothing / fixed-point updates with one dense joint posterior.
rng = np.random.default_rng(812)
d, na, nb = 6, 5, 7
worst = dict(mean=0., covariance=0., cross=0., fixed_mean=0., fixed_covariance=0.)

def spd(scale):
    a = rng.normal(size=(d, d))
    return scale * (a @ a.T / d + np.eye(d))

def transition():
    # Three unrecorded material/transport steps folded into one recorded edge.
    f, q = np.eye(d), np.zeros((d, d))
    for _ in range(3):
        g = np.eye(d) + .07 * rng.normal(size=(d, d))
        f, q = g @ f, g @ q @ g.T + spd(.025)
    return f, q

def observation():
    n = int(rng.integers(1, 3))
    h = rng.normal(size=(n, d))
    return h, np.eye(n) * .15, rng.normal(size=n)

def update(m, p, obs):
    h, r, y = obs
    s = h @ p @ h.T + r
    k = np.linalg.solve(s, h @ p).T
    return m + k @ (y - h @ m), p - k @ h @ p

def filtering(m, p, edges, obs):
    mf, pf, mp, pp, gains = [m], [p], [m], [p], []
    for (f, q), z in zip(edges, obs):
        pred, cov = f @ mf[-1], f @ pf[-1] @ f.T + q
        gains.append(np.linalg.solve(cov, f @ pf[-1]).T)
        mp.append(pred); pp.append(cov)
        m, p = update(pred, cov, z)
        mf.append(m); pf.append(p)
    ms, ps = list(mf), list(pf)
    for k in range(len(edges)-1, -1, -1):
        g = gains[k]
        ms[k] = mf[k] + g @ (ms[k+1] - mp[k+1])
        ps[k] = pf[k] + g @ (ps[k+1] - pp[k+1]) @ g.T
    return ms, ps, gains

def batch(m, p, arms):
    n = 1 + sum(len(edges) for edges, _ in arms)
    info, eta = np.zeros((n*d, n*d)), np.zeros(n*d)
    ip = np.linalg.inv(p)
    info[:d, :d], eta[:d] = ip, ip @ m
    node = 1
    for edges, obs in arms:
        parent = 0
        for (f, q), (h, r, y) in zip(edges, obs):
            a, b = slice(parent*d, (parent+1)*d), slice(node*d, (node+1)*d)
            iq = np.linalg.inv(q)
            info[a,a] += f.T @ iq @ f
            info[a,b] -= f.T @ iq
            info[b,a] -= iq @ f
            info[b,b] += iq + h.T @ np.linalg.solve(r, h)
            eta[b] += h.T @ np.linalg.solve(r, y)
            parent, node = node, node+1
    covariance = np.linalg.inv(info)
    return covariance @ eta, covariance

for trial in range(100):
    m0, p0 = update(rng.normal(size=d), spd(2.), observation())
    ea, eb = [transition() for _ in range(na)], [transition() for _ in range(nb)]
    za, zb = [observation() for _ in range(na)], [observation() for _ in range(nb)]
    ma, pa, ga = filtering(m0, p0, ea, za)
    mb, pb, _ = filtering(ma[0], pa[0], eb, zb)
    truth, cov = batch(m0, p0, [(ea, za), (eb, zb)])
    _, acov = batch(m0, p0, [(ea, za)])
    product = np.eye(d)
    for j in range(na+1):
        if j:
            product = product @ ga[j-1]
        cross = pa[j] @ product.T
        sl = slice(j*d, (j+1)*d)
        worst['cross'] = max(worst['cross'], np.max(abs(cross-acov[sl,:d])))
        gain = np.linalg.solve(pa[0], cross.T).T
        m = ma[j] + gain @ (mb[0] - ma[0])
        p = pa[j] + gain @ (pb[0] - pa[0]) @ gain.T
        worst['mean'] = max(worst['mean'], np.max(abs(m-truth[sl])))
        worst['covariance'] = max(worst['covariance'], np.max(abs(p-cov[sl,sl])))

    # Track only the inner endpoint of arm A while filtering arm B.
    mt, pt, c = ma[-1].copy(), pa[-1].copy(), cross.copy()
    m, p = ma[0].copy(), pa[0].copy()
    for (f, q), (h, r, y) in zip(eb, zb):
        m, p, c = f @ m, f @ p @ f.T + q, c @ f.T
        s = h @ p @ h.T + r
        kt = np.linalg.solve(s, h @ c.T).T
        k = np.linalg.solve(s, h @ p).T
        mt += kt @ (y-h @ m)
        pt -= kt @ s @ kt.T
        c = c @ (np.eye(d)-k @ h).T
        m, p = m+k @ (y-h @ m), p-k @ h @ p
    sl = slice(na*d, (na+1)*d)
    worst['fixed_mean'] = max(worst['fixed_mean'], np.max(abs(mt-truth[sl])))
    worst['fixed_covariance'] = max(worst['fixed_covariance'], np.max(abs(pt-cov[sl,sl])))

print('100 random 6D two-arm systems; 5 + 7 edges; three material substeps per edge')
for name, error in worst.items():
    print(f'{name}: max absolute error {error:.3e}')
assert max(worst.values()) < 1e-10
