import uproot
import awkward as ak
import numpy as np
import pandas as pd
import scipy.stats
from scipy.optimize import curve_fit


def material_label(material):
    if material == "fe":
        return "Fe"
    if material == "lar":
        return "LAr"
    raise ValueError(f"Unknown material: {material}")


def read_g4_data(path, min_p_out):
    g4_data = ak.to_dataframe(uproot.open(path)["reading"].arrays(library="ak"))
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
        def gauss(x, m, s):
            return 1 / (s * (2 * np.pi) ** 0.5) * np.exp(-0.5 * ((x - m) / s) ** 2)

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

            p0 = median, mm1s - mp1s
            params, cov = curve_fit(gauss, centers, binned, p0=p0, maxfev=1000000)

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
    return loc


def fwhm_landau(loc, scale):
    pdf_max = scipy.stats.landau.pdf(loc, loc, scale)
    left_space = np.linspace(0, loc, 10000)
    left = left_space[
        np.argmax(scipy.stats.landau.pdf(left_space, loc, scale) > pdf_max / 2)
    ]
    right_space = np.linspace(loc, 4 * loc, 10000)
    right = right_space[
        np.argmax(scipy.stats.landau.pdf(right_space, loc, scale) < pdf_max / 2)
    ]
    return left, right


def fwhm_to_std(fwhm):
    return fwhm * 0.42466090014400953


def stat_fwhm_landau(data):
    loc, scale = fit_landau(data)
    left, right = fwhm_landau(loc, scale)
    return right - left


def stat_fwhm_std_landau(data):
    loc, scale = fit_landau(data)
    left, right = fwhm_landau(loc, scale)
    fwhm = abs(right - left)
    return fwhm_to_std(fwhm)
