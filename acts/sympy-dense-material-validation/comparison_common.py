import uproot
import awkward as ak
import numpy as np
import pandas as pd
import scipy.stats
from scipy.optimize import curve_fit, minimize_scalar, brentq


def material_label(material):
    if material == "fe":
        return "Fe"
    if material == "lar":
        return "LAr"
    raise ValueError(f"Unknown material: {material}")


def read_g4_data(path, min_p_out):
    g4_data = ak.to_dataframe(uproot.open(path)["reading"].arrays(library="ak"))
    # Legacy muon files store kinetic energies under the p_* names. New files
    # carry explicit kinetic_* columns and store actual momenta in p_*.
    if "kinetic_initial" not in g4_data:
        mass = 0.1056583755  # muon mass in GeV
        for stage in ("initial", "final"):
            kinetic = g4_data[f"p_{stage}"].copy()
            g4_data[f"kinetic_{stage}"] = kinetic
            g4_data[f"p_{stage}"] = np.sqrt(kinetic * (kinetic + 2 * mass))
    g4_data = g4_data[g4_data["p_final"] > min_p_out]

    return g4_data


def read_acts_data(path, min_p_out=None):
    acts_data = pd.read_csv(path)

    if min_p_out is not None:
        acts_data = acts_data[acts_data["p_final"] > min_p_out]

    return acts_data


def make_g4_msc_stats(g4_data, edges, log_range):
    g4_e_init = g4_data["p_initial"]
    g4_x = g4_data["x"]

    g4_std, _, _ = scipy.stats.binned_statistic(
        g4_e_init,
        g4_x,
        bins=edges,
        range=log_range,
        statistic=stat_robust_std,
    )
    g4_std_std, _, _ = scipy.stats.binned_statistic(
        g4_e_init,
        g4_x,
        bins=edges,
        range=log_range,
        statistic=stat_robust_std_std,
    )

    return g4_std, g4_std_std


def make_acts_msc_stats(acts_data, edges, log_range):
    acts_std, _, _ = scipy.stats.binned_statistic(
        acts_data["p_initial"],
        acts_data["x_sigma"],
        bins=edges,
        range=log_range,
        statistic=stat_mean,
    )

    return acts_std


def make_g4_eloss_stats(g4_data, edges, log_range):
    g4_e_init = g4_data["p_initial"]
    g4_e_loss = g4_data["e_loss"]

    g4_mode, _, _ = scipy.stats.binned_statistic(
        g4_e_init,
        g4_e_loss,
        bins=edges,
        range=log_range,
        statistic=stat_mode_landau,
    )
    g4_mean, _, _ = scipy.stats.binned_statistic(
        g4_e_init,
        g4_e_loss,
        bins=edges,
        range=log_range,
        statistic=stat_mean,
    )
    g4_std, _, _ = scipy.stats.binned_statistic(
        g4_e_init,
        g4_e_loss,
        bins=edges,
        range=log_range,
        statistic=stat_fwhm_std_landau,
    )

    return g4_mode, g4_mean, g4_std


def robust_gauss_fit_naive(data):
    def fit(data):
        return np.mean(data), np.std(data)

    for _ in range(3):
        m, s = fit(data)
        data = data[np.abs(data - np.median(data)) < 3 * s]

    return (m, s), np.zeros((2, 2))


def robust_gauss_fit(data):
    def fit(data):
        def gauss(x, amplitude, m, s):
            return amplitude * np.exp(-0.5 * ((x - m) / s) ** 2)

        try:
            if len(data) < 20:
                raise ValueError(f"Not enough data to fit a Gaussian: {len(data)}")

            low, mp1s, median, mm1s, high = np.percentile(data, [1, 16, 50, 84, 99])
            hist_range = (low, high)
            bins = 30
            binned, edges = np.histogram(
                data, range=hist_range, bins=bins, density=True
            )
            centers = 0.5 * (edges[1:] + edges[:-1])

            # density=True normalizes the truncated histogram, not the full
            # Gaussian. Fit its normalization instead of biasing the width.
            p0 = np.max(binned), median, (mm1s - mp1s) / 2
            params, cov = curve_fit(
                gauss,
                centers,
                binned,
                p0=p0,
                maxfev=1000000,
                bounds=([0, -np.inf, np.finfo(float).tiny], [np.inf] * 3),
            )
            params, cov = params[1:], cov[1:, 1:]

            if cov[1, 1] > 5 * params[1] ** 2:
                raise ValueError(
                    f"Fit failed, covariance too large: {cov[1, 1]} > {5 * params[1] ** 2}"
                )
        except Exception as e:
            print(f"Falling back to naive mean/std. Error: {e}")
            params, cov = (np.mean(data), np.std(data)), np.zeros((2, 2))

        return params, cov

    for _ in range(3):
        (m, s), cov = fit(data)
        data = data[np.abs(data - m) < 3 * s]

    return (m, s), cov


def stat_mean(data):
    if len(data) == 0:
        return None
    return np.mean(data)


def stat_std(data):
    s = np.std(data)
    return s


def stat_robust_std(data):
    if len(data) == 0:
        return None
    (_, s), _ = robust_gauss_fit(data)
    return s


def stat_robust_std_std(data):
    if len(data) == 0:
        return None
    (_, _), cov = robust_gauss_fit(data)
    return np.sqrt(cov[1, 1])


def fit_landau(data):
    if len(data) == 0:
        return None, None
    loc, scale = scipy.stats.landau.fit(data, method="mle")
    return loc, scale


def stat_mode_landau(data):
    loc, scale = fit_landau(data)
    if loc is None:
        return None
    return loc + scale * _LANDAU_MODE


# scipy.stats.landau uses a standard distribution whose mode is not zero.
_LANDAU_MODE = minimize_scalar(
    lambda x: -scipy.stats.landau.pdf(x), bounds=(-2, 2), method="bounded"
).x
_LANDAU_HALF_MAX = scipy.stats.landau.pdf(_LANDAU_MODE) / 2
_LANDAU_LEFT = brentq(
    lambda x: scipy.stats.landau.pdf(x) - _LANDAU_HALF_MAX, -10, _LANDAU_MODE
)
_LANDAU_RIGHT = brentq(
    lambda x: scipy.stats.landau.pdf(x) - _LANDAU_HALF_MAX, _LANDAU_MODE, 100
)


def fwhm_landau(loc, scale):
    return loc + scale * _LANDAU_LEFT, loc + scale * _LANDAU_RIGHT


def fwhm_to_std(fwhm):
    return fwhm * 0.42466090014400953


def stat_fwhm_landau(data):
    loc, scale = fit_landau(data)
    if loc is None:
        return None
    left, right = fwhm_landau(loc, scale)
    return right - left


def stat_fwhm_std_landau(data):
    loc, scale = fit_landau(data)
    if loc is None:
        return None
    left, right = fwhm_landau(loc, scale)
    fwhm = abs(right - left)
    return fwhm_to_std(fwhm)
