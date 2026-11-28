import pathlib, base64, json, hashlib, shutil, sys
import numpy as np, pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from markdown_it import MarkdownIt

root = pathlib.Path(sys.argv[1])
publish = root / "publish"
publish.mkdir(exist_ok=True)
slug = "2026-10-31_sympy-dense-material-residuals"
assets = publish / slug
assets.mkdir(exist_ok=True)
s = pd.read_csv(root / "summary.csv")
a = pd.read_csv(root / "acts.csv")
r = pd.read_csv(root / "rates.csv")
j = pd.read_csv(root / "threshold.csv")
old = pd.read_csv(root / "before-threshold-fix/threshold.csv")
c = s.merge(a[a["mode"] == "mean"], on=["material", "p", "L"], suffixes=["", "_acts"])
c["screen_G4_ACTS"] = c.screen_core / c.screen_sigma
c["angle_G4_ACTS"] = c.angle_core / c.angle_sigma
c["screen_G4_ACTS_se"] = c.screen_se / c.screen_sigma
c.to_csv(root / "comparison.csv", index=False)
plt.rcParams.update(
    {
        "font.size": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "figure.constrained_layout.use": True,
    }
)
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for ax, mat in zip(axs, ["Fe", "lAr"]):
    for mode, label, color in [
        ("constant_uncut", "Scattering only, large electron cut", "C0"),
        ("full", "Full FTFP_BERT", "C1"),
    ]:
        chosen = ((c["mode"] == "constant_uncut") & (c.p < 100)) | (
            (c["mode"] == "constant_all") & (c.p == 100)
        )
        d = c[
            (c.material == mat)
            & (chosen if mode == "constant_uncut" else c["mode"] == mode)
            & (c.h == 10)
            & (c.L == 1000)
        ].sort_values("p")
        y = d.screen_ratio if mode == "constant_uncut" else d.screen_G4_ACTS
        err = (
            d.screen_se / d.screen_highland
            if mode == "constant_uncut"
            else d.screen_G4_ACTS_se
        )
        ax.errorbar(d.p, y, yerr=err, marker="o", label=label, color=color)
    ax.axhline(1, color="k", lw=0.8)
    ax.set(
        xscale="log",
        xlabel="Initial momentum [GeV]",
        ylabel="Geant4 core / matching ACTS sigma",
        title=f"{mat}: 1 m, step cap 10 mm",
        ylim=(0.91, 1.01),
    )
    ax.legend(fontsize=8)
for ext in ["png", "pdf"]:
    fig.savefig(assets / f"controlled-scattering.{ext}", dpi=180)
plt.close(fig)
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
d = s[
    (s.material == "Fe") & (s.p == 10) & (s.L == 1000) & (s["mode"] == "constant")
].sort_values("h")
axs[0].errorbar(
    d.h,
    d.screen_ratio,
    yerr=d.screen_se / d.screen_highland,
    marker="o",
    label="Screen width",
)
axs[0].errorbar(
    d.h,
    d.angle_ratio,
    yerr=d.angle_se / d.theta_highland,
    marker="s",
    label="Exit angular width",
)
axs[0].set(
    xscale="log",
    xlabel="Geant4 maximum step [mm]",
    ylabel="Geant4 core / ACTS",
    title="Fe, 10 GeV, loss off; electron cut 1 mm",
)
axs[0].legend()
for mat, col in [("Fe", "C0"), ("lAr", "C1")]:
    d = s[
        (s.material == mat)
        & (s.p == 10)
        & (s.h == 10)
        & (s["mode"] == "constant_uncut")
    ]
    x = np.fromfile(root / f"{mat}_10_1000_10_constant_uncut.bin").reshape(-1, 12)
    x = x[x[:, 0] == 2, 3] / float(d.theta_highland.iloc[0])
    hist, edges = np.histogram(x, bins=160, range=(-5, 5), density=True)
    pd.DataFrame({"center": (edges[1:] + edges[:-1]) / 2, "density": hist}).to_csv(
        assets / f"{mat}-angular-histogram.csv", index=False
    )
    axs[1].stairs(hist, edges, label=mat, color=col)
x = np.linspace(-5, 5, 1001)
axs[1].plot(x, np.exp(-x * x / 2) / np.sqrt(2 * np.pi), "k--", label="ACTS Gaussian")
axs[1].set(
    yscale="log",
    ylim=(1e-4, 1),
    xlabel="Exit direction y / Highland sigma",
    ylabel="Density",
    title="Scattering only, large electron cut",
)
axs[1].legend()
for ext in ["png", "pdf"]:
    fig.savefig(assets / f"step-size-and-shape.{ext}", dpi=180)
plt.close(fig)
fig, axs = plt.subplots(1, 2, figsize=(11, 4))
for mat, ax in zip(["Fe", "lAr"], axs):
    d = r[r.material == mat]
    for key, label in [
        ("acts", "ACTS Bethe"),
        ("matched_density_I", "ACTS with G4 density effect and I"),
        ("g4_plain_bethe", "G4BetheBlochModel"),
    ]:
        ax.plot(d.p, d[key] / d.g4, marker=".", label=label)
    ax.axhline(1, color="k", lw=0.8)
    ax.set(
        xscale="log",
        xlabel="Momentum [GeV]",
        ylabel="Stopping power / G4 muIoni",
        title=mat,
    )
    ax.legend(fontsize=8)
for ext in ["png", "pdf"]:
    fig.savefig(assets / f"ionisation-components.{ext}", dpi=180)
plt.close(fig)


def table(headers, rows):
    return (
        "| "
        + " | ".join(headers)
        + " |\n|"
        + "|".join(["---"] * len(headers))
        + "|\n"
        + "".join("| " + " | ".join(map(str, row)) + " |\n" for row in rows)
    )


full = c[(c["mode"] == "full") & (c.h == 10) & (c.L == 1000)].sort_values(
    ["material", "p"]
)
tfull = table(
    [
        "Material",
        "p [GeV]",
        "Screen G4/ACTS",
        "Angle G4/ACTS",
        "Mean final p: G4 / ACTS [GeV]",
    ],
    [
        (
            d.material,
            f"{d.p:g}",
            f"{d.screen_G4_ACTS:.4f} ± {d.screen_G4_ACTS_se:.4f}",
            f"{d.angle_G4_ACTS:.4f}",
            f"{d.pout_mean:.6f} / {d.pout:.6f}",
        )
        for d in full.itertuples()
    ],
)
pure = s[
    (
        ((s["mode"] == "constant_uncut") & (s.p < 100))
        | ((s["mode"] == "constant_all") & (s.p == 100))
    )
    & (s.h == 10)
].sort_values(["material", "p"])
tpure = table(
    [
        "Material",
        "p [GeV]",
        "Screen core / ACTS",
        "Angle core / ACTS",
        "Angle RMS / ACTS",
    ],
    [
        (
            d.material,
            f"{d.p:g}",
            f"{d.screen_ratio:.4f} ± {d.screen_se/d.screen_highland:.4f}",
            f"{d.angle_ratio:.4f}",
            f"{d.angle_rms/d.theta_highland:.4f}",
        )
        for d in pure.itertuples()
    ],
)
step = c[(c["mode"] == "full") & (c.L == 1000)].sort_values(["material", "p", "h"])
tstep = table(
    ["Material", "p [GeV]", "Step cap [mm]", "Screen G4/ACTS", "Angle G4/ACTS"],
    [
        (
            d.material,
            f"{d.p:g}",
            "No effective user limit" if d.h > 1e8 else f"{d.h:g}",
            f"{d.screen_G4_ACTS:.4f} ± {d.screen_G4_ACTS_se:.4f}",
            f"{d.angle_G4_ACTS:.4f}",
        )
        for d in step.itertuples()
    ],
)
jj = j[(j.h == 1) & (j.epsilon == 0.001)]
oo = old[(old.h == 1) & (old.epsilon == 0.001)]
tjac = table(
    [
        "Initial p [GeV]",
        "Before jump correction",
        "After",
        "Exact endpoint-flow ratio",
        "Finite difference",
    ],
    [
        (
            f"{d.p:g}",
            f"{oo[oo.p==d.p].jac.iloc[0]:.9f}",
            f"{d.jac:.9f}",
            f"{d.exact:.9f}",
            f"{d.fd:.9f}",
        )
        for d in jj.itertuples()
    ],
)
energy = r[(r.p.isin([4, 10, 100]))].sort_values(["material", "p"])
trate = table(
    ["Material", "p [GeV]", "ACTS", "ACTS + G4 δ,I", "G4 plain Bethe", "G4 muIoni"],
    [
        (
            d.material,
            f"{d.p:g}",
            f"{d.acts:.6f}",
            f"{d.matched_density_I:.6f}",
            f"{d.g4_plain_bethe:.6f}",
            f"{d.g4:.6f}",
        )
        for d in energy.itertuples()
    ],
)
body = f"""

## 31.10.2026 — follow-up: isolate the remaining differences

This follow-up supersedes the earlier “cause not established” verdict and the open threshold-Jacobian limitation. The earlier measurements are retained as the record of the first investigation.

### Findings

- Generate **43 controlled samples × 150,000 primary muons = 6,450,000 events**, using Geant4 **11.3.2**, `FTFP_BERT`, zero magnetic field, and matched Fe/LAr material densities and radiation lengths.
- A residual scattering-model difference remains with nearly constant momentum and complete electron-scattering coverage: screen core widths are about **4–5% below ACTS in iron**, **2–3% below ACTS in liquid argon** for these 1 m examples. Extra energy-loss processes cannot explain this control result.
- Geant4 step size changes lateral displacement more than angular spread. The previously inactive user limit explains roughly **1–2 percentage points** of additional screen-width deficit in the sampled full-physics cases. The exact historical offset is not reconstructed: the old Geant4 version and random sample are unknown.
- Turning off ionisation also removes delta-ray recoil angles. A valid scattering-only control must account for the production cut. Raising the electron cut restores that scattering within the scattering models and increases the screen core by about **1–2 percentage points**.
- Isolate the low-energy stopping-power mismatch: ACTS's asymptotic density correction differs from Geant4's material-dependent correction. At higher energies, Geant4's muon-ionisation model has additional corrections; agreement of the total loss can hide component cancellations.
- Fix the remaining ACTS Jacobian issue at discontinuous loss-model thresholds. The endpoint momentum and physical loss/scattering parameterizations are unchanged. Numerical validation passes; the remaining width differences are not evidence of an unresolved RK integration error in these homogeneous tests.

### Controlled setup and observables

- Negative muons at true initial momentum **4, 10, 100 GeV**; slab thickness **1000 mm**, plus constant-energy checks at **10 and 100 mm**. Gun x = −1500 mm; slab centred at zero; screen entrance x = +1500 mm. World and screen material are vacuum. Slab transverse half-size is half its thickness; screen half-size is 500 mm.
- One binary record per generated primary, including outcome status, slab-exit position/direction/momentum, screen position/direction/momentum, and actual material path. Count the first screen crossing only. Kill secondary tracks after creation; their primary recoil and energy transfer remain.
- Fe X0 = **17.5749346509709 mm**, density **7.874 g/cm³**; LAr X0 = **140.0343868497 mm**, density **1.396 g/cm³**, matching ACTS's predefined materials. Excitation energies remain different and are examined separately.
- Actual process log reports `msc` model **WentzelVIUni**, plus `CoulombScat`. These are complementary parts of the combined scattering model. Disabling Coulomb scattering alone is not a complete scattering reference.
- Modes: `full` = the full physics list; `ion` = transport + scattering + muIoni; `constant` = transport + scattering only with default 1 mm production range cut; `constant_uncut` = scattering only with a very large production range cut; `constant_all` = scattering only with an explicit electron energy cut above all tested transfers; `msc` = MSC without CoulombScat; `ioncsda` = ionisation + scattering, loss fluctuations disabled, very large production cut.
- `constant_uncut` uses a 10⁹ mm production range cut and requests an expanded cut-conversion energy range. The actual converted electron cut is **9549.93 MeV** in both materials, sufficient at 4 and 10 GeV but not at 100 GeV. For the 100 GeV reference, `constant_all` explicitly supplies a **10⁹ MeV electron energy cut** through `SetEnergyCutVector`, updates the couple table and rebuilds physics tables; process logs verify the actual value. The completed-cut table/plot below uses this control at 100 GeV. Retain the original range-cut sample as a diagnostic. A 10 GeV Fe duplicate checks that raising an already sufficient energy cut leaves the result compatible. Small nuclear-recoil losses remain: roughly 24 keV in 1 m Fe and 4 keV in LAr, negligible relative to the removed GeV-scale ionisation loss. Thus “constant” is an approximation, quantified here.
- Fit only transverse **y**, one observation per surviving primary, using the corrected free-amplitude Gaussian core fitter. Also record full RMS and the central 68.27% half-width. The fitted core is an observable with a fit convention, not the full variance.
- Quoted width errors are empirical standard errors from **15 blocks** of each 150,000-event sample. They do not include model or fit-window systematics. Use all screen survivors; there is **no outgoing-momentum cut**. At 10 mm cap, full-physics acceptance is at least **99.978%**; constant-energy runs retain all primaries. The new samples therefore avoid the old near-stopping-range selection ambiguity.

### Full-physics result

All ratios are **Geant4 / ACTS**. ACTS uses its mean-loss trajectory, 1 mm cap and tolerance 10⁻¹⁰. Geant4 uses a 10 mm user cap in this table.

{tfull}

![Controlled scattering comparison]({slug}/controlled-scattering.png)

For 4 GeV iron, G4 loses about 1.397 GeV versus ACTS 1.428 GeV: a roughly **2.2% difference in loss**, but only a modest change in the predicted scattering width. Holding the ACTS scattering formula fixed and replacing its momentum history with an independently integrated unrestricted G4 ionisation history changes the screen sigma from **53.57343 to 53.28316 mm (−0.54%)**. This diagnostic excludes radiative processes on the G4-history side; it is not a claim of an exact total-loss decomposition.

At 10 and 100 GeV the total mean endpoints agree much more closely, while the scattering offset persists. At 4 GeV iron the measured mean path is **1000.531 mm**, only **0.053%** beyond the nominal thickness. Path elongation is too small to explain the percent-level loss or width differences here.

### Scattering without changing momentum

Use the large electron cut so that switching off `muIoni` does not leave out its above-cut electron-recoil scattering. Compare with the ACTS material accumulator evaluated at fixed momentum, not with its slowing-down trajectory.

{tpure}

The 10 GeV Fe 1 mm-cap large-cut control gives screen ratio **0.9559** and angular ratio **0.9459**; the residual does not disappear with the smaller cap. This isolates a difference between Highland's Gaussian approximation and Geant4's WentzelVI/Coulomb angular distribution and transport, rather than energy-loss stacking.

The default-cut “constant” control is intentionally retained as a diagnostic. At 10 GeV / 1 m Fe / 10 mm cap its screen ratio is **0.9435**, versus **0.9549** with the large cut. For LAr it changes from **0.9659 to 0.9816**. Simply disabling muIoni would therefore overstate the scattering-model deficit.

For Fe at the same momentum and geometry, disabling `CoulombScat` as well gives **0.9106** instead of **0.9435** with it enabled. That difference is a missing part of Geant4's mixed scattering prescription, not evidence that independent Highland and Coulomb widths should be added.

RMS and fitted core differ, particularly in thinner material in radiation-length units. The table and archived summaries retain both. Matching a core width by rescaling ACTS would not establish that its tails, covariance, or another thickness agree.

Geant4 source evidence: the Wentzel cross section limits electron scattering using the production cut, and its transport combines nuclear/electron contributions. This explains why the process toggle alone is insufficient:
https://raw.githubusercontent.com/Geant4/geant4/v11.3.2/source/processes/electromagnetic/standard/src/G4WentzelOKandVIxSection.cc

### Geant4 step dependence and covariance geometry

Full-physics scan; “no effective user limit” sets the cap to 10⁹ mm, leaving the physics/geometry limiters active. Independent finite samples mean differences smaller than the quoted errors are not significant.

{tstep}

At fixed 10 GeV with loss off and the default production cut, Fe screen ratios at **1, 10, 100 mm** caps are **0.9482, 0.9435, 0.9209**, whereas angular ratios are **0.9386, 0.9357, 0.9400**. The broad angular agreement alongside the lateral shift locates this effect in spatial transport. This is separate from ACTS RK accuracy.

![Step size and angular distributions]({slug}/step-size-and-shape.png)

ACTS integrates increments of accumulated Highland variance rather than constant scattering power. At constant momentum, write

- `F(s) = C s [A + b log(s/L)]²`, with `A = 1 + 0.038 log(L/(X0 β²))`, `b = 0.038`, and `F(L) = θ_H²`.
- `mean(s)/L = 1/2 + b/(2A) − b²/(4A²)` under the normalized variance-increment measure `dF/F(L)`.
- `mean(s²)/L² = 1/3 + 4b/(9A) − 4b²/(27A²)`.
- For screen distance `D = 1500 + L/2` from the slab entrance, `Var(y_screen) = θ_H² [D² − 2D mean(s) + mean(s²)]`.

These analytic moments agree with the existing ACTS accumulator to **2.1×10⁻⁵ relative in screen sigma** over the constant-momentum cases. The finite substep size accounts for the small difference. This independently checks the accumulation/transport arithmetic.

For 1 m Fe the Highland cumulative-log weighting moves scattering slightly later in the slab than uniform diffusion. The predicted screen/angular lever is about **1511 mm**, versus **1527.5 mm** for uniform scattering power. The fine-step G4 large-cut control gives **1527.0 mm**. This roughly **1% geometric weighting effect partly compensates the angular-model discrepancy**; it is not the dominant cause of ACTS predicting a wider screen core.

Geant4's lateral displacement is sampled separately from its final direction, and its algorithms have step-size dependence. Relevant source and model documentation:
https://raw.githubusercontent.com/Geant4/geant4/v11.3.2/source/processes/electromagnetic/standard/src/G4WentzelVIModel.cc
https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/elastic_scattering/msc.html

### Which energy-loss differences remain

Compare unrestricted ionisation rates at fixed momentum, in **MeV/mm**. “ACTS + G4 δ,I” algebraically substitutes Geant4's density correction and excitation energy into the ACTS Bethe expression; it does not change production ACTS code. The plain G4 Bethe model is initialized separately after building the physics tables. It includes its own corrections and is not the muon-specific high-energy model selected by `muIoni`.

{trate}

- At **4 GeV Fe**, ACTS → matched δ,I shifts **1.442513 → 1.410750 MeV/mm**; G4 muIoni gives **1.416662**. The density/I approximation explains the main excess and other corrections partly compensate it. The corresponding LAr values are **0.264551 → 0.259117 → 0.260203**.
- At **100 GeV Fe**, changing δ,I hardly changes ACTS (**1.690886 → 1.690840**), while plain G4 Bethe gives **1.700186** and muIoni gives **1.733757**. The residual here is principally additional model corrections, not an integration defect or a material-I mismatch.
- At **10 GeV**, near-equality of the original total ionisation rates is partly cancellation: matching δ,I alone moves ACTS away from the full muIoni value.
- G4's high-energy muon ionisation model includes radiative corrections to muon–electron scattering in addition to the leading Bethe expression. These are distinct from separately enabled muBrems/muPairProd processes:
  https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/muon_incident/muion.html

![Ionisation component comparison]({slug}/ionisation-components.png)

Turning on ionisation, then full physics, changes both the momentum history and recoil distribution. At 10 GeV Fe with 10 mm cap, the full screen ratio is **0.9556** versus **0.9500** for ionisation plus scattering; at 4 GeV the two agree within sampling errors (**0.9391 vs 0.9410**). Extra processes are not the main origin of the 4–6% residual.

The 4 GeV Fe `ioncsda` control gives screen ratio **0.9400** and final mean momentum **2.603119 GeV**, compared with **0.9410 / 2.607796 GeV** for `ion`. Its width does not reveal a large fluctuation-induced core shift. This is a joint change of fluctuation setting and production cut, not a clean one-variable fluctuation measurement. Independently integrating G4 unrestricted ionisation over exactly 1000 mm gives **2.608555 GeV**; the large-cut/no-fluctuation run is not identical to that scalar reference. No exact attribution of this few-MeV difference is claimed.

The component study establishes where the dominant discrepancies enter. It does not separately measure every bremsstrahlung/pair/photonuclear mean or validate Landau mode/FWHM against a fresh complete loss-spectrum scan. Those observables need their own distribution comparison; they cannot be inferred from these screen-core results.

### Fix: Jacobians at stopping-power discontinuities

ACTS's loss parameterization jumps at `βγ = 10`, and for muons also at total energies **8 GeV and 1 TeV**. A correct smooth derivative on either side cannot represent the change in crossing time.

For the autonomous scalar equation `q′ = f(q)`, the exact fixed-path derivative is `J = f(q_final)/f(q_initial)`. Crossing a threshold requires a saltation factor `f_after/f_before`; at fixed q/p the kinematic factor cancels, leaving `loss_after/loss_before`. In the full free-state system only the q/p flow component jumps, so the jump matrix is the identity except for its q/p diagonal.

Implementation in the local ACTS worktree:

- Share threshold constants between the material functions and the dense stepper in `Core/include/Acts/Material/detail/EnergyLossConstants.hpp`.
- On an accepted step crossing a threshold, evaluate the one-sided stopping powers, extrapolating their smooth derivatives back to the boundary to avoid the float branch ambiguity.
- Apply the jump factor to the q/p Jacobian row; compensate the scaled q/p column so that other plain Jacobian rows remain unchanged at the crossing.
- Respect `dense.includeGradient`; do not alter the endpoint state or the mean/mode loss formula. Apply nothing on rejected trials.
- Place the correction at the accepted crossing-step endpoint. The adaptive RK controller resolves the loss jump; the placement error tends to zero with the crossing step. This is not an exact event-root solver. Validation covers the resulting position, direction, time and q/p derivatives.

Zero field, mean loss, 1 m Fe, tolerance 10⁻¹⁰, 1 mm cap:

{tjac}

Before correction the 2 GeV Jacobian is low by about **0.924%**; the 1005 GeV Jacobian is high by about **6.75%**. After correction the three values agree with the exact scalar relation at approximately **10⁻⁶ relative or better**. A 0.1 mm cap gives the same result. Finite-difference scans at relative q/p perturbations 10⁻³, 3×10⁻⁴, 10⁻⁴ expose float/adaptive-step noise at the smallest perturbations; the endpoint-flow identity supplies an independent reference.

Tests cover both charges, forward/backward propagation, mean/mode loss, and B = 0 or 2 T, crossing all three thresholds. Compare q/p to the analytic identity and finite differences, and compare time and magnetic deflection derivatives to finite differences. The very small TeV time derivative is omitted from the finite-difference time assertion because subtracting total flight times loses precision.

The physical discontinuities themselves remain. In particular, LAr's asymptotic density correction becomes negative just above βγ = 10. This study preserves that approximation and handles its derivative consistently; adopting a continuous material-dependent density model is a separate physics-model change.

### Validation, reproducibility and status

- New threshold regression and the full Sympy unit, material unit, and dense integration suites pass: **8,881 test cases, 184,634 assertions** (Sympy 11 / 78,492; material 4,974 / 39,910; integration 3,896 / 66,232). Logs are archived below.
- ACTS source changes, including this threshold fix, remain local. The earlier thesis comparison fixes and labels remain pushed in commit `2d1f78b6d7540f6212cef2c5596368083c0004f2`. This follow-up does not retune ACTS to force agreement with Geant4.
- Code: `acts/sympy-dense-material-validation/followup` in https://github.com/andiwand/cern-scripts. Includes Geant4 driver, process-toggle matrices, ACTS/analytic comparisons, stopping-power diagnostics, fitter snapshot, and report generator. README gives commands and the binary record layout.
- Evidence: [{slug}/]({slug}/). Archive numerical summaries, both threshold tables, process logs, statistical widths, angular histograms, plots/PDFs, cut-check and test logs, and a complete ACTS patch including the new header.
- Raw per-event binary samples remain in `/tmp/acts-dense-followup` for this session (approximately 619 MB for the 43 production samples). They are not copied into the notes repository. The archived run matrix, source and seeds reproduce them; the saved summaries and histograms preserve the reported measurements without committing large temporary simulation files.
- Fit/model/systematic uncertainty, unknown historical Geant4 version, finite sample statistics, and the joint cut/fluctuation control limit an exact percentage-by-percentage reconstruction of the old curves. The dominant remaining mechanisms are now isolated; this is not a claim that the two physical models are equivalent.
"""
(publish / "appendix.md").write_text(body)
html = MarkdownIt("commonmark", {"html": False}).enable("table").render(body)
for file in assets.glob("*.png"):
    html = html.replace(
        f'src="{slug}/{file.name}"',
        f'src="data:image/png;base64,{base64.b64encode(file.read_bytes()).decode()}"',
    )
(publish / "appendix.html").write_text(html)
for name in [
    "summary.csv",
    "comparison.csv",
    "acts.csv",
    "rates.csv",
    "g4ion-covariance.csv",
    "threshold.csv",
    "unit-tests.log",
    "material-tests.log",
    "integration-tests.log",
    "cutcheck.log",
    "cutcheck_all.log",
    "cutcheck_lar.log",
]:
    shutil.copy2(root / name, assets / name)
shutil.copy2(
    root / "before-threshold-fix/threshold.csv", assets / "threshold-before.csv"
)
logs = assets / "geant4-logs"
logs.mkdir(exist_ok=True)
for p in root.glob("*.bin"):
    if p.stat().st_size != 150000 * 12 * 8:
        continue
    for ext in [".log", ".bin.material"]:
        src = p.with_suffix(ext)
        if src.exists():
            shutil.copy2(src, logs / src.name)
print("Report appendix and artifacts prepared", len(body.split()), "words")
