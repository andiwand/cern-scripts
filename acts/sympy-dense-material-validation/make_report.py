"""Create the dated Markdown, offline HTML, figures and evidence bundle."""

import argparse
import base64
from pathlib import Path
import shutil

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from markdown_it import MarkdownIt

parser = argparse.ArgumentParser()
parser.add_argument("data", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
data = args.data
output = args.output
slug = "2026-10-31_sympy-dense-material-geant4"
assets = output / slug
assets.mkdir(parents=True, exist_ok=True)
for name in [
    "numerics.csv",
    "rates.csv",
    "current-screen.csv",
    "historical-comparison.csv",
    "historical-comparison.png",
    "historical-comparison.pdf",
    "reanalyse.log",
    "acts-fixes.patch",
    "thesis-fixes.patch",
    "unit-patched.log",
    "material-patched.log",
    "integration-patched.log",
    "codegen.log",
    "thesis-build.log",
    "thesis-smoke-fixed.log",
]:
    shutil.copy2(data / name, assets / name)
shutil.copytree(
    data / "patched-results", assets / "patched-results", dirs_exist_ok=True
)


def read(name):
    return np.genfromtxt(
        data / name, names=True, delimiter=",", dtype=None, encoding="utf-8"
    )


old = read("numerics.csv")
new = read("patched-results/numerics.csv")
rates = read("rates.csv")
history = read("historical-comparison.csv")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for rows, label, marker in [(old, "Before", "o"), (new, "Patched", "s")]:
    s = rows[(rows["material"] == "Fe") & (rows["p_GeV"] == 2)]
    axes[0].plot(
        s["h_mm"],
        abs(s["p_out_GeV"] - s["reference_halfstep_GeV"]) * 1000,
        marker + "-",
        label=label,
    )
axes[0].set(
    xscale="log",
    yscale="log",
    xlabel="Maximum step [mm]",
    ylabel="Absolute final momentum error [MeV]",
    title="2 GeV muon, 1 m iron, zero field",
)
axes[0].legend()
axes[0].grid(alpha=0.2)
for name, label in [("Fe", "Iron"), ("lAr", "Liquid argon"), ("Si", "Silicon")]:
    s = rates[rates["material"] == name]
    axes[1].plot(
        s["p_GeV"], s["acts_ion_MeV_mm"] / s["g4_ion_MeV_mm"], "o-", label=label
    )
axes[1].axhline(1, color="k", linewidth=0.8)
axes[1].set(
    xscale="log",
    xlabel="Muon momentum [GeV]",
    ylabel="ACTS / Geant4 ionisation stopping power",
    title="Physics difference before transport",
)
axes[1].legend()
axes[1].grid(alpha=0.2)
fig.tight_layout()
fig.savefig(assets / "numerics-and-stopping-power.png", dpi=160)
fig.savefig(assets / "numerics-and-stopping-power.pdf")

numeric_table = "| Step cap [mm] | Before p_final [GeV] | Patched p_final [GeV] | Reference [GeV] |\n|---:|---:|---:|---:|\n"
for h in [1000, 100, 10, 1]:
    a = old[(old["material"] == "Fe") & (old["p_GeV"] == 2) & (old["h_mm"] == h)][0]
    b = new[(new["material"] == "Fe") & (new["p_GeV"] == 2) & (new["h_mm"] == h)][0]
    numeric_table += f"| {h} | {a['p_out_GeV']:.9f} | {b['p_out_GeV']:.9f} | {b['reference_halfstep_GeV']:.9f} |\n"

msc_table = "| Material, 1 m | Initial p bin [GeV] | Original interpretation | Correct p | Correct p + free fit amplitude |\n|---|---:|---:|---:|---:|\n"
for r in history:
    if r["thickness_mm"] == 1000 and (3 < r["p_low"] < 4 or 90 < r["p_low"] < 120):
        msc_table += f"| {r['material']} | {r['p_low']:.2f}–{r['p_high']:.2f} | {r['msc_old']:.4f} | {r['msc_corrected']:.4f} | {r['msc_corrected_free_amplitude']:.4f} |\n"

rate_table = "| Material | p [GeV] | ACTS ionisation [MeV/mm] | Geant4 unrestricted [MeV/mm] | Difference |\n|---|---:|---:|---:|---:|\n"
for r in rates:
    if r["material"] in ["Fe", "lAr"] and r["p_GeV"] in [1, 10, 100]:
        ratio = r["acts_ion_MeV_mm"] / r["g4_ion_MeV_mm"] - 1
        rate_table += f"| {r['material']} | {r['p_GeV']:g} | {r['acts_ion_MeV_mm']:.6f} | {r['g4_ion_MeV_mm']:.6f} | {ratio:+.2%} |\n"

report = f"""# Sympy dense-material integration and the Geant4 comparison

## 31.10.2026

Companion page: [{slug}.html]({slug}.html).
Code: `acts/sympy-dense-material-validation` in https://github.com/andiwand/cern-scripts.
Evidence and patches: [{slug}/]({slug}/).

### Verdict

- Both implementation defects and comparison defects are present. The original disagreement cannot be assigned entirely to additional Geant4 processes.
- Fix the numerical error control, stopping-power Jacobian, final path derivative, and three shared material derivative errors in the ACTS `dev3` worktree.
- Fix the thesis reader/writer, ratio labels, Gaussian fit normalization, Landau mode/FWHM, and Geant4 screen recording. Enable the requested Geant4 step limiter.
- A 2 GeV muon through 1 m of iron has a 28.2 MeV endpoint momentum error with one original step. With adaptive energy-loss control the error is below 3 keV in the tested step-cap scan.
- After correcting the historical comparison, a scattering-core discrepancy remains: roughly 5–8% for 1 m iron and 3–4% for 1 m liquid argon in the quoted bins. Its cause is not established by this study.
- A separate limitation remains for Jacobians crossing the model's abrupt density-correction threshold. No physical stopping-power or scattering model is retuned here.

### Repository status

- Thesis comparison fixes, including both ratio labels, are committed and pushed: https://github.com/andiwand/cern-thesis/commit/2d1f78b6d7540f6212cef2c5596368083c0004f2
- ACTS implementation changes remain local in the `dev3` worktree. This note and its validation scripts are saved locally.

### Scope and provenance

- ACTS base: `5bbaa63f5d332b24627a44eb76f23bb6f2e53f67`, source `~/cern/source/acts/acts/dev3`; existing build `~/cern/build/acts/acts/dev3`.
- Baseline executable links the existing ACTS core. The patched executable and tests compile the changed material/stepper sources and freshly generated kernel, linking the remaining dependencies from the same build. Original and patched numerical outputs are archived separately.
- Fresh Geant4 11.3.2 stopping powers use initialized `FTFP_BERT`, `G4EmCalculator::ComputeDEDX`, and the local 11.3 datasets. `BeamOn(0)` builds the physics tables before queries. The unrestricted cut is `DBL_MAX`.
- Historical simulation: the six saved `logscale_mom_{{fe,lar}}_{{10,100,1000}}mm.root` files and matching ACTS CSVs in `~/cern/thesis/data/dense-propagation`. The historical Geant4 binary version is not recovered. Its source uses `FTFP_BERT` and activates muon ionisation, bremsstrahlung, pair production, and photonuclear interactions.
- Reanalysis uses existing Geant4 events; it is not a new million-event production. A fresh 10,000-primary Geant4 run validates the corrected recorder.

### ACTS fixes

1. **Energy loss participates in adaptive stepping.** The old dense error estimate uses only the three direction accelerations. At zero magnetic field it is identically zero, independent of the error in momentum or time. The new estimate also includes the time slope and the q/p slope normalized by q/p, with the same length units and fourth-root controller. This adds no new public tolerance option. The regression starts from a 1 m trial step and compares against an independent scalar energy integration.
2. **Differentiate stopping power at every RK stage.** The old symbolic expressions treat the four stopping-power samples as constants. The chain rule now includes `d(dE/ds)/d(q/p)` from the material functions; `dense.includeGradient` controls it. Spatial material gradients and field gradients are still outside this approximation.
3. **Correct the final q/p path derivative.** The dense kernel stores the final q/p in the derivative slot. It now stores the last-stage q/p slope, consistent with the other last-stage acceleration entries. This matters for surface/path corrections to the covariance. The vacuum-material case must give zero.
4. **Correct shared material derivatives.** `deriveBeta2` lacks a factor of beta squared; the numerator in the logarithmic derivative of maximum energy transfer has the wrong signs; the Landau derivative uses `-0.2` where the value function uses `+0.2`. Finite-difference tests cover both charge signs, absolute charges 1 and 2, muon/proton mass scales, and beta-gamma values 0.5–100 away from discontinuities. The loss value functions are unchanged.

The unmodified dense unit tests and telescope covariance cases pass before these fixes; they do not test these failure modes. The telescope starts with almost zero covariance, and its normal-incidence geometry does not expose the wrong q/p surface correction through the transverse scattering width.

### Independent integration result

Zero field, negative muon, homogeneous iron, initial momentum 2 GeV, path 1000 mm. The reference solves `dE/ds = -computeEnergyLossMean` directly in energy with fixed-step RK4, then converts energy to momentum. It does not reuse the Sympy q/p integration. Halving the reference step from 0.02 to 0.01 mm changes the result by 0.020 keV at most in the nine material/momentum reference cases.

{numeric_table}

Original error control rejects no steps even at `stepTolerance = 1e-10`. The patched scan uses `1e-6` and reaches the requested path with adaptive substeps; `h_mm` in its CSV is the cap, not the accepted step length. Its 1000 mm iron trial produces nine rejected trials. The existing float-valued material functions and their abrupt threshold prevent assuming smooth fourth-order convergence through every energy.

At 10 GeV in 1 m iron, the transported `d(q/p_final)/d(q/p_initial)` changes from **1.39609766** to **1.37584725**, agreeing with finite differences (**1.37584758**) in the 10 mm-cap case. The final q/p path derivative changes from approximately **-0.118155** to **-2.12921e-5 GeV^-1 mm^-1**.

![Numerical and stopping-power checks]({slug}/numerics-and-stopping-power.png)

### Thesis comparison fixes

- **Kinetic energy is not momentum.** The Geant4 writer calls `GetKineticEnergy()` for both `p_initial` and `p_final`. Existing files satisfy `p_initial - p_final = e_loss` to roundoff, confirming their meaning. The reader now converts legacy muon data with `p = sqrt(T*(T+2m))` before applying momentum cuts or binning. New output stores actual momenta plus explicit `kinetic_initial` and `kinetic_final`; those columns identify the new schema. Old ROOT files are preserved.
- **Both stacked ratio plots are labelled backwards.** They calculate `Geant4 / ACTS`. The axis labels now say `Geant4 / ACTS`.
- **The Gaussian core fitter biases the width.** The histogram covers the 1st–99th percentiles and is renormalized by `density=True`, but the fit fixes the full Gaussian normalization. A million standard-normal samples give sample sigma **0.998693**, old fitted sigma **0.984768**, corrected fitted sigma **1.001234**. Fit normalization independently and retain the mean/width covariance submatrix. The screen plot uses the same helper.
- **SciPy Landau `loc` is not its mode.** The standardized mode is about **-0.429314**; use `loc + scale*mode`. Obtain the FWHM from half-height roots of the standardized PDF rather than a scan bounded by `0`, `loc`, and `4*loc`. This also works for zero/negative location parameters.
- **A sensitive screen can record a primary more than once.** The first smoke run has 10,001 rows for 10,000 primaries. Record only the first crossing per track/event, use the pre-step entrance-plane state for all final quantities, and write an event ID. The corrected run has exactly **10,000 distinct events and 10,000 rows**. Legacy files lack event IDs, so the reanalysis cannot remove historical duplicates reliably.
- **The configured Geant4 maximum step was inactive.** The detector requests 1 mm through `G4UserLimits`, but registration of `G4StepLimiterPhysics` is commented out in both production drivers. Register it. Also preserve fractional kinetic energies in the single-energy command rather than truncating to an integer.

### What remains in the saved Geant4 comparison

For each surviving Geant4 primary, evaluate the archived ACTS position sigma at that event's initial momentum and fit the distribution of `x/sigma_ACTS`. This removes unequal momentum distributions inside bins. The table keeps the same events in all columns: true outgoing momentum > 2 GeV. Values are **Geant4 core width / ACTS sigma**, not their inverse.

{msc_table}

![Historical comparison corrections]({slug}/historical-comparison.png)

- The current ACTS stepper reproduces the archived predicted position sigmas within 0.02% for p > 3 GeV over the 10/100/1000 mm Fe/LAr scan. The numerical/Jacobian fixes do not change those finely stepped, almost-zero-initial-covariance predictions at the displayed precision.
- In the 3.61–4.84 GeV bin, the corrected mean energy-loss ratios for 1 m Fe and LAr are **0.9794 ± 0.0006** and **0.9857 ± 0.0016**. At 92.28–123.91 GeV they are **1.0001 ± 0.0092** and **0.9974 ± 0.0182**. Uncertainties here are empirical standard errors of the mean only; they do not include model, selection, or historical duplication effects.
- These are screen-crossing samples, not unconditional incident-particle samples. Stopped, decayed, or missed-screen particles are absent. Outgoing-momentum cuts select a different tail population near the stopping range. A Gaussian core width and a full RMS are different observables. The free-amplitude fit still has a chosen fit range and should not be interpreted as a unique physical variance.

### Physics differences and interactions that combine

Direct fresh-Geant4 unrestricted ionisation comparison, before integrating a trajectory:

{rate_table}

The ACTS material helpers use `I = 16 eV * Z^0.9`: about 300.33 eV for iron and 215.71 eV for liquid argon, versus 286 and 188 eV in these Geant4 NIST materials. ACTS uses an asymptotic density correction switched at beta-gamma 10. Geant4 also has more detailed model corrections. Matching I alone is therefore insufficient; at high energy it cancels algebraically against I in ACTS's asymptotic density correction. The rate CSV includes a matched-I diagnostic.

Geant4 splits loss into continuous restricted stopping power and explicit above-cut secondaries. At 10 GeV in iron, unrestricted ionisation is **1.525625 MeV/mm**, but the same calculation restricted to 1 MeV transfers gives **1.090853 MeV/mm**, a 28.5% difference. Comparing that restricted quantity directly with ACTS Bethe loss is invalid. Use total primary energy loss, or explicitly match the cut convention. Killing secondaries after their creation does not undo energy already lost by the primary.

At 100 GeV in iron, ACTS radiation loss is **0.502159 MeV/mm**; Geant4 bremsstrahlung plus pair loss is **0.425055 MeV/mm**. This is deliberately not presented as a total-radiation disagreement: the ACTS muon parameterization includes a photonuclear contribution, and that Geant4 pair of terms excludes it. Good agreement in the total can mask opposing component differences.

Adding processes changes the energy history, so the final loss with several processes is not generally the sum of final losses from independent single-process runs. Scattering also changes path length; fluctuations change the distribution sampled by subsequent energy-dependent interactions. Even a perfectly integrated deterministic `dE/ds = -g(E)` does not generally equal the mean endpoint of stochastic transport, since `E[g(E)] != g(E[E])`.

Sources:

- https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/energy_loss/enloss.html
- https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/energy_loss/fluctuations.html
- https://geant4.web.cern.ch/documentation/pipelines/master/prm_html/PhysicsReferenceManual/electromagnetic/muon_incident/pair.html
- https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/TrackingAndPhysics/userLimits.html

### Remaining limitation and next discriminating comparisons

The density correction has an abrupt switch at beta-gamma 10, corresponding to p about 1.0566 GeV for a muon. Smooth analytical stopping-power derivatives do not represent the jump when a trajectory crosses this threshold. The patched 2 GeV / 1 m iron case still has approximately a 1% q/p-Jacobian disagreement with finite differences, although its endpoint momentum is accurate. The smooth 10 and 100 GeV cases agree. A continuous, physically specified density-effect model or an explicit treatment of the jump is needed to remove this limitation; silently smoothing it would change the mean-loss model and is not done here.

The remaining scattering-core offset is not diagnosed conclusively. A useful next comparison is:

1. Match material constants and tabulate each unrestricted stopping-power component at fixed momentum.
2. Compare deterministic integrations using the same stopping-power function and matched path length.
3. In Geant4, isolate ionisation and add bremsstrahlung, pairs, photonuclear interactions, scattering, fluctuations, and decay in controlled configurations. Record actual material path length, initial momentum, exit momentum, and every stopped/decayed/missed outcome.
4. Compare the same mean, mode, core width, and RMS definitions separately. Scan production cuts and maximum step, and report survival fractions. Do not tune ACTS to a combined plot while these conditions differ.

### Validation and files

- Symbolic generator checks pass with stopping-power gradients included.
- Sympy stepper: **10 cases, 5,418 assertions pass** (includes three new regressions).
- Material interactions: **4,974 cases, 39,910 assertions pass** (includes new finite-difference derivative coverage).
- Dense Sympy integration: **3,896 cases, 66,232 assertions pass**.
- Both modified Geant4 drivers compile. Fresh 10,000-primary smoke run checks unique screen crossings, momentum/kinetic-energy consistency, and energy balance.
- Python checks cover known Gaussian width, Landau half-height roots, legacy/new ROOT schemas, and outgoing-momentum cuts.
- ACTS/thesis diffs pass whitespace checks. Original simulation data and existing dated notes are preserved.

Implementation patches: [ACTS]({slug}/acts-fixes.patch), [thesis comparison]({slug}/thesis-fixes.patch).
Data: [before]({slug}/numerics.csv), [patched]({slug}/patched-results/numerics.csv), [stopping powers]({slug}/rates.csv), [historical comparison]({slug}/historical-comparison.csv).
The build/test harness and report generator live in the scripts repository, not in the notes evidence directory.
"""
(output / (slug + ".md")).write_text(report)
body = MarkdownIt("commonmark").enable("table").render(report)
for name in ["numerics-and-stopping-power.png", "historical-comparison.png"]:
    encoded = base64.b64encode((assets / name).read_bytes()).decode()
    body = body.replace(
        f'src="{slug}/{name}"', f'src="data:image/png;base64,{encoded}"'
    )
css = """
:root{--bg:#f5f7f9;--panel:#fff;--fg:#15202b;--muted:#4c5a67;--line:#d7dde3;--accent:#1f5f8b}
@media(prefers-color-scheme:dark){:root{--bg:#14181d;--panel:#1c2229;--fg:#e8ecf0;--muted:#b4bec8;--line:#313b45;--accent:#6fb0e0;color-scheme:dark}}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0;padding:30px 16px 70px}
main{max-width:1080px;margin:auto;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:32px}
h1{font-size:2rem;line-height:1.2}h2{font-size:1rem;color:var(--muted)}h3{font-size:1.22rem;margin-top:2em;border-top:1px solid var(--line);padding-top:1em}
p,li{max-width:95ch}li{margin:.35em 0}a{color:var(--accent);overflow-wrap:anywhere}code{font:0.88em ui-monospace,SFMono-Regular,monospace;overflow-wrap:anywhere}
img{width:100%;height:auto;border-radius:5px;background:white}table{border-collapse:collapse;width:100%;font-size:.88em;display:block;overflow-x:auto;margin:20px 0}td,th{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left}th{background:var(--bg)}
@media(max-width:650px){main{padding:18px}body{padding:10px}h1{font-size:1.55rem}}
@media print{body{background:white;padding:0}main{border:0;padding:0}h3{break-after:avoid}img,table{break-inside:avoid}}
"""
(output / (slug + ".html")).write_text(
    '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Sympy dense material and Geant4 — 31.10.2026</title><style>"
    + css
    + "</style><main>"
    + body
    + "</main></html>"
)
print(output / (slug + ".md"))
print(output / (slug + ".html"))
