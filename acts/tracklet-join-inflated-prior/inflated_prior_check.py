"""Check of the two-way CKF join when pass 2 starts from the pass-1 smoothed
parameters with an inflated covariance c * P_A instead of P_A itself.

Two linear-Gaussian arms share node 0 (the state s). Arm A is pass 1, arm B
is pass 2. The reference is one dense joint posterior over both arms.

Checked identities, for every inflation factor c:
  1. pass-2 MBF smoother + carried adjoint at the prior node = RTS step onto
     the prior node (m'_s, P'_s), the posterior given B and the inflated prior;
  2. combination at s with the inflated prior subtracted once,
     Y_AB = P_A^-1 + P'_s^-1 - (c P_A)^-1, equals the joint posterior at s;
  3. the same in MBF form: re-anchor the pass-2 adjoint from the prior c P_A
     to the prior P_A with one 6x6 solve, then apply it to (m_A, P_A);
  4. the conditioning walk over pass 1 (RTS form and MBF form) and the new
     walk over pass 2 reproduce every state of the joint posterior;
  5. the regression coefficients of the walks do not depend on the prior;
  6. a wrong prior mean for pass 2 does not change the exact result;
  7. the error of the combination without the subtraction, as a function of c.
Also run with a short pass 2 whose measurements do not constrain all six
parameters (rank-deficient Y_B).
"""
import sys
import numpy as np

rng = np.random.default_rng(812)
d = 6
TOL = 1e-8


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


def observation(nmax=2):
    n = int(rng.integers(1, nmax + 1))
    h = rng.normal(size=(n, d))
    return h, np.eye(n) * .15, rng.normal(size=n)


def update(m, p, obs):
    h, r, y = obs
    s = h @ p @ h.T + r
    k = np.linalg.solve(s, h @ p).T
    return m + k @ (y - h @ m), p - k @ h @ p


class Chain:
    """One filtered arm: node 0 is the prior node (no measurement), nodes
    1..n carry one measurement each. Stores what the ACTS EDM stores (predicted
    and filtered mean and covariance, jacobian) plus K, H, S, r for the MBF."""

    def __init__(self, m0, p0, edges, obs):
        self.n = len(edges)
        self.F = [None]; self.Q = [None]
        self.mp = [m0]; self.pp = [p0]; self.mf = [m0]; self.pf = [p0]
        self.H = [None]; self.S = [None]; self.K = [None]; self.r = [None]
        m, p = m0, p0
        for (f, q), (h, r, y) in zip(edges, obs):
            mp, pp = f @ m, f @ p @ f.T + q
            s = h @ pp @ h.T + r
            k = np.linalg.solve(s, h @ pp).T
            res = y - h @ mp
            m, p = mp + k @ res, pp - k @ h @ pp
            self.F.append(f); self.Q.append(q)
            self.mp.append(mp); self.pp.append(pp); self.mf.append(m); self.pf.append(p)
            self.H.append(h); self.S.append(s); self.K.append(k); self.r.append(res)

    def rts_gains(self):
        return [None] + [np.linalg.solve(self.pp[k], self.F[k] @ self.pf[k - 1]).T
                         for k in range(1, self.n + 1)]

    def rts(self):
        """RTS smoother over nodes n..0, the step onto node 0 is the prior-node step."""
        g = self.rts_gains()
        ms, ps = list(self.mf), list(self.pf)
        for k in range(self.n, 0, -1):
            ms[k - 1] = self.mf[k - 1] + g[k] @ (ms[k] - self.mp[k])
            ps[k - 1] = self.pf[k - 1] + g[k] @ (ps[k] - self.pp[k]) @ g[k].T
        return ms, ps

    def mbf(self):
        """Modified Bryson-Frazier smoother. Returns the smoothed states and the
        adjoint (lambda, Lambda) carried to the prior node 0."""
        ms, ps = list(self.mf), list(self.pf)
        lam, Lam = np.zeros(d), np.zeros((d, d))   # post-update adjoint of node n
        for k in range(self.n, 0, -1):
            c = np.eye(d) - self.K[k] @ self.H[k]
            hs = self.H[k].T @ np.linalg.solve(self.S[k], self.H[k])
            Lam_hat = hs + c.T @ Lam @ c
            lam_hat = -self.H[k].T @ np.linalg.solve(self.S[k], self.r[k]) + c.T @ lam
            ms[k] = self.mp[k] - self.pp[k] @ lam_hat
            ps[k] = self.pp[k] - self.pp[k] @ Lam_hat @ self.pp[k]
            lam, Lam = self.F[k].T @ lam_hat, self.F[k].T @ Lam_hat @ self.F[k]
        ms[0] = self.mp[0] - self.pp[0] @ lam
        ps[0] = self.pp[0] - self.pp[0] @ Lam @ self.pp[0]
        return ms, ps, lam, Lam

    def regression_rts(self, ps):
        """L_k = Cov(x_k, x_0) Var(x_0)^-1 from the RTS gain products."""
        g = self.rts_gains()
        out, prod = [np.eye(d)], np.eye(d)
        for k in range(1, self.n + 1):
            prod = prod @ g[k]
            cross = ps[k] @ prod.T
            out.append(np.linalg.solve(ps[0], cross.T).T)
        return out

    def regression_mbf(self, ps):
        """L_k = T_k Z from the sensitivity sweeps, no covariance inverse but
        the one of the smoothed node 0 in Z."""
        Dp, Df = [np.eye(d)], [np.eye(d)]
        for k in range(1, self.n + 1):
            dp = self.F[k] @ Df[k - 1]
            Dp.append(dp); Df.append((np.eye(d) - self.K[k] @ self.H[k]) @ dp)
        T = [None] * (self.n + 1)
        Psi = np.zeros((d, d))   # post-update adjoint sensitivity of node n
        for k in range(self.n, 0, -1):
            T[k] = Df[k] - self.pf[k] @ Psi
            c = np.eye(d) - self.K[k] @ self.H[k]
            Psi_hat = self.H[k].T @ np.linalg.solve(self.S[k], self.H[k]) @ Dp[k] + c.T @ Psi
            Psi = self.F[k].T @ Psi_hat
        T[0] = np.eye(d) - self.pf[0] @ Psi
        Z = np.linalg.solve(ps[0].T, self.pp[0].T).T   # Pp_0 Ps_0^-1
        return [t @ Z for t in T]


def batch(m, p, arms):
    """Dense joint posterior over node 0 and all arm nodes."""
    n = 1 + sum(len(edges) for edges, _ in arms)
    info, eta = np.zeros((n * d, n * d)), np.zeros(n * d)
    ip = np.linalg.inv(p)
    info[:d, :d], eta[:d] = ip, ip @ m
    node = 1
    for edges, obs in arms:
        parent = 0
        for (f, q), (h, r, y) in zip(edges, obs):
            a, b = slice(parent * d, (parent + 1) * d), slice(node * d, (node + 1) * d)
            iq = np.linalg.inv(q)
            info[a, a] += f.T @ iq @ f
            info[a, b] -= f.T @ iq
            info[b, a] -= iq @ f
            info[b, b] += iq + h.T @ np.linalg.solve(r, h)
            eta[b] += h.T @ np.linalg.solve(r, y)
            parent, node = node, node + 1
    cov = np.linalg.inv(info)
    return cov @ eta, cov


def condition(ms, ps, L, dm, dP):
    return ([m + l @ dm for m, l in zip(ms, L)],
            [p + l @ dP @ l.T for p, l in zip(ps, L)])


def run(label, na, nb, nmax, factors, trials=100):
    print(f'\n== {label}: {trials} random 6D systems, {na} + {nb} edges, '
          f'measurements of dimension 1..{nmax}, three material substeps per edge')
    keys = ['prior node rts vs mbf', 'combination cov form', 'combination mbf form',
            'walk pass1 rts', 'walk pass1 mbf', 'walk pass2 rts', 'walk pass2 mbf',
            'regression prior free', 'wrong prior mean', 'pass2 filter vs dense']
    worst = {c: dict.fromkeys(keys, 0.) for c in factors}
    approx = {c: dict(width_min=1., width_max=1., shift=0.) for c in factors}
    for _ in range(trials):
        m0, p0 = update(rng.normal(size=d), spd(2.), observation())
        ea, eb = [transition() for _ in range(na)], [transition() for _ in range(nb)]
        za, zb = [observation(nmax) for _ in range(na)], [observation(nmax) for _ in range(nb)]
        A = Chain(m0, p0, ea, za)
        msA, psA, _, _ = A.mbf()
        mA, PA = msA[0], psA[0]
        truth, cov = batch(m0, p0, [(ea, za), (eb, zb)])
        LA = A.regression_mbf(psA)
        LA_rts = A.regression_rts(psA)
        L_ref = None
        for c in factors:
            w = worst[c]
            Pc = c * PA
            B = Chain(mA, Pc, eb, zb)
            msB, psB, lam_c, Lam_c = B.mbf()
            # diagnostic: the pass-2 filter alone against a dense fit with the same inflated prior
            tB, cB = batch(mA, Pc, [(eb, zb)])
            w['pass2 filter vs dense'] = max(w['pass2 filter vs dense'],
                                             abs(B.mf[-1] - tB[-d:]).max(), abs(B.pf[-1] - cB[-d:, -d:]).max())
            msB_rts, psB_rts = B.rts()
            w['prior node rts vs mbf'] = max(w['prior node rts vs mbf'],
                                             abs(msB[0] - msB_rts[0]).max(), abs(psB[0] - psB_rts[0]).max())
            ms_prime, Ps_prime = msB[0], psB[0]
            # (2) covariance form with the prior subtracted once
            iPA, iPs, iPc = np.linalg.inv(PA), np.linalg.inv(Ps_prime), np.linalg.inv(Pc)
            Y = iPA + iPs - iPc
            P_AB = np.linalg.inv(Y)
            m_AB = P_AB @ (iPA @ mA + iPs @ ms_prime - iPc @ mA)
            w['combination cov form'] = max(w['combination cov form'],
                                            abs(m_AB - truth[:d]).max(), abs(P_AB - cov[:d, :d]).max())
            # (3) MBF form: re-anchor the adjoint from c*PA to PA
            M = np.eye(d) - (Pc - PA) @ Lam_c
            Lam_A = np.linalg.solve(M.T, Lam_c.T).T          # Lam_c M^-1
            lam_A = lam_c + Lam_A @ (Pc - PA) @ lam_c
            m_AB2 = mA - PA @ lam_A
            P_AB2 = PA - PA @ Lam_A @ PA
            w['combination mbf form'] = max(w['combination mbf form'],
                                            abs(m_AB2 - truth[:d]).max(), abs(P_AB2 - cov[:d, :d]).max())
            # (4) walks
            m1, p1 = condition(msA, psA, LA_rts, m_AB - mA, P_AB - PA)
            for k in range(na + 1):
                sl = slice(k * d, (k + 1) * d)
                w['walk pass1 rts'] = max(w['walk pass1 rts'], abs(m1[k] - truth[sl]).max(), abs(p1[k] - cov[sl, sl]).max())
            m1, p1 = condition(msA, psA, LA, m_AB - mA, P_AB - PA)
            for k in range(na + 1):
                sl = slice(k * d, (k + 1) * d)
                w['walk pass1 mbf'] = max(w['walk pass1 mbf'], abs(m1[k] - truth[sl]).max(), abs(p1[k] - cov[sl, sl]).max())
            LB = B.regression_mbf(psB)
            LB_rts = B.regression_rts(psB)
            for form, L in (('walk pass2 rts', LB_rts), ('walk pass2 mbf', LB)):
                m2, p2 = condition(msB, psB, L, m_AB - ms_prime, P_AB - Ps_prime)
                for k in range(1, nb + 1):
                    sl = slice((na + k) * d, (na + k + 1) * d)
                    w[form] = max(w[form], abs(m2[k] - truth[sl]).max(), abs(p2[k] - cov[sl, sl]).max())
            # (5) regression coefficients of pass 2 are prior independent
            if L_ref is None:
                L_ref = LB
            else:
                w['regression prior free'] = max(w['regression prior free'],
                                                 max(abs(a - b).max() for a, b in zip(LB, L_ref)))
            # (6) wrong prior mean, exact subtraction
            m_wrong = mA + rng.normal(size=d) * np.sqrt(np.diag(PA)) * 3.
            Bw = Chain(m_wrong, Pc, eb, zb)
            msW, psW, lam_w, Lam_w = Bw.mbf()
            iPw = np.linalg.inv(psW[0])
            Yw = iPA + iPw - iPc
            m_w = np.linalg.solve(Yw, iPA @ mA + iPw @ msW[0] - iPc @ m_wrong)
            Lam_wA = np.linalg.solve((np.eye(d) - (Pc - PA) @ Lam_w).T, Lam_w.T).T
            lam_wA = lam_w + Lam_wA @ ((Pc - PA) @ lam_w - (m_wrong - mA))
            m_w2 = mA - PA @ lam_wA
            w['wrong prior mean'] = max(w['wrong prior mean'], abs(m_w - truth[:d]).max(),
                                        abs(np.linalg.inv(Yw) - cov[:d, :d]).max(), abs(m_w2 - truth[:d]).max())
            # (7) no subtraction
            Ya = iPA + iPs
            Pa = np.linalg.inv(Ya)
            ma = Pa @ (iPA @ mA + iPs @ ms_prime)
            ratio = np.sqrt(np.diag(Pa) / np.diag(P_AB))
            approx[c]['width_min'] = min(approx[c]['width_min'], ratio.min())
            approx[c]['width_max'] = max(approx[c]['width_max'], ratio.max())
            approx[c]['shift'] = max(approx[c]['shift'], (abs(ma - m_AB) / np.sqrt(np.diag(P_AB))).max())
    print(f'{"max abs error":28s}' + ''.join(f'{"c=" + str(c):>12s}' for c in factors))
    for key in keys:
        print(f'{key:28s}' + ''.join(f'{worst[c][key]:12.1e}' for c in factors))
    print('no subtraction: pull-width factor min / max, mean shift in sigma (max over states and trials)')
    for c in factors:
        a = approx[c]
        print(f'  c={c:<8g} width {a["width_min"]:.4f} / {a["width_max"]:.4f}, shift {a["shift"]:.2e}, '
              f'1/sqrt(1+1/c) = {1 / np.sqrt(1 + 1 / c):.4f}')
    bad = max(worst[c][k] for c in factors if c <= ASSERT_UP_TO
              for k in keys if k != 'pass2 filter vs dense')
    assert bad < TOL, bad
    return worst, approx


ASSERT_UP_TO = 1000
factors = [1, 4, 10, 100, 1000, 1e6]
run('pass 2 constrains all six parameters', na=5, nb=7, nmax=2, factors=factors)
run('short pass 2, rank-deficient Y_B', na=5, nb=2, nmax=1, factors=factors)
print(f'\nall join identities hold to {TOL} for c <= {ASSERT_UP_TO}; c = 1e6 and the filter '
      'diagnostic (absolute error on quantities of size c) are reported only')
