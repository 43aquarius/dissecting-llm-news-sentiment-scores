#!/usr/bin/env python3
"""Figures v2 (audit paper). Style: charts.md conventions
(no top/right spines, dashed grid, no in-figure titles, constrained_layout)."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

for f in ["/usr/share/fonts/truetype/chinese/NotoSansSC-Regular.ttf",
          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
    try: fm.fontManager.addfont(f)
    except Exception: pass
plt.rcParams.update({
    "font.sans-serif": ["DejaVu Sans", "Noto Sans SC"],
    "axes.unicode_minus": False,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.linestyle": "--", "grid.alpha": 0.35,
    "figure.dpi": 150, "savefig.dpi": 200,
    "font.size": 9.5, "axes.titlesize": 10.5,
})
C = {"main": "#2563eb", "alt": "#d97706", "grey": "#6b7280",
     "neg": "#dc2626", "pos": "#059669", "sand": "#b45309"}
DATA = "/home/z/my-project/data"
OUT = f"{DATA}/figures"

arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
r1 = json.load(open(f"{DATA}/llm_scores_rep1.json"))
r2 = json.load(open(f"{DATA}/llm_scores_rep2.json"))
r3 = json.load(open(f"{DATA}/llm_scores_rep3.json"))
R2 = json.load(open(f"{DATA}/results_v2.json"))
R1 = json.load(open(f"{DATA}/results.json"))

inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
def arr(src, field="sentiment"):
    return np.array([src.get(a["url"], {}).get(field) for a in inwin], dtype=float)
s_o, s_a, s_1, s_2, s_3 = arr(orig), arr(anon), arr(r1), arr(r2), arr(r3)
lm_a = np.array([a.get("lm_tone") for a in inwin], dtype=float)

# ---------------- Fig 1: score distributions named vs anonymized ----------------
fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), constrained_layout=True)
ax = axes[0]
bins = np.arange(-100, 101, 10)
ax.hist(s_o, bins=bins, alpha=0.62, color=C["main"], label="named", density=True)
ax.hist(s_a, bins=bins, alpha=0.62, color=C["alt"], label="anonymized", density=True)
ax.set_xlabel("sentiment score (-100..+100)")
ax.set_ylabel("density")
ax.legend(frameon=False, loc="upper left")
ax.annotate(f"mean shift = +4.75\n(paired t = 5.14)",
            xy=(0.03, 0.93), xycoords="axes fraction", va="top", fontsize=8.5, color=C["grey"])
ax = axes[1]
d = s_o - s_a
ax.hist(d[np.isfinite(d)], bins=np.arange(-60, 61, 5), color=C["main"], alpha=0.8, density=True)
ax.axvline(0, color="black", lw=0.8)
ax.axvline(d.mean(), color=C["neg"], lw=1.4, ls="--", label=f"mean {d.mean():.2f}")
ax.set_xlabel("named $-$ anonymized score")
ax.legend(frameon=False)
fig.savefig(f"{OUT}/fig_scores_named_anon.png")
plt.close(fig)

# ---------------- Fig 2: repeat-call reliability ----------------
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.3), constrained_layout=True)
ax = axes[0]
j = 1.2 + 0.18 * np.random.default_rng(7).normal(size=len(s_o))
ax.scatter(s_o + j * 0, s_1, s=9, alpha=0.38, color=C["main"], edgecolors="none")
lims = [-105, 105]
ax.plot(lims, lims, color=C["grey"], lw=0.9, ls="--")
ax.set_xlim(lims); ax.set_ylim(lims)
ax.set_xlabel("original score"); ax.set_ylabel("repeat-call score (draw 1)")
r_pair = np.corrcoef(s_o[~np.isnan(s_o * s_1)], s_1[~np.isnan(s_o * s_1)])[0, 1]
exact_pair = np.nanmean(s_o == s_1)
ax.annotate(f"Pearson r = {r_pair:.3f}\npairwise exact = {exact_pair:.1%}", xy=(0.04, 0.06),
            xycoords="axes fraction", fontsize=8.5, color=C["grey"])
ax = axes[1]
# within-article SD across 4 draws
X4 = np.column_stack([s_o, s_1, s_2, s_3])
sd = np.nanstd(X4, axis=1, ddof=1)
ax.hist(sd[np.isfinite(sd)], bins=np.arange(0, 25, 1.5), color=C["main"], alpha=0.8, density=True)
ax.set_xlabel("within-headline SD over 4 calls")
exact_all = R2["h3_stability"]["exact_identical_all4"]
ax.annotate(f"mean SD = 7.8\nICC(2,4) = 0.919\nall-4 identical = {exact_all:.1%}",
            xy=(0.55, 0.93), xycoords="axes fraction",
            va="top", fontsize=8.5, color=C["grey"])
ax = axes[2]
# Bland-Altman: mean vs |diff| for named-anon vs repeat noise
m4 = np.nanmean(X4, axis=1)
noise_sd = sd
mask = np.isfinite(s_o - s_a) & np.isfinite(noise_sd)
ax.scatter(m4[mask], np.abs(s_o - s_a)[mask], s=9, alpha=0.4, color=C["alt"],
           edgecolors="none", label="named vs anon |diff|")
ax.scatter(m4[mask], noise_sd[mask] * np.sqrt(2), s=9, alpha=0.4, color=C["grey"],
           edgecolors="none", label=r"repeat-noise $SD\times\sqrt{2}$")
ax.set_xlabel("mean score over 4 calls")
ax.set_ylabel("absolute difference")
ax.legend(frameon=False, loc="upper left", fontsize=8)
fig.savefig(f"{OUT}/fig_reliability.png")
plt.close(fig)

# ---------------- Fig 3: coefficient forest plot ----------------
rows = [
    ("H1: named, baseline", R2["h1_baseline"]["coef"], R2["h1_baseline"]["se"], C["main"]),
    ("H1: named, +same-day ret", R2["h1_baseline"]["plus_sameday_ctrl"]["coef"],
     R2["h1_baseline"]["plus_sameday_ctrl"]["coef"] / R2["h1_baseline"]["plus_sameday_ctrl"]["t"], C["main"]),
    ("H2: anonymized", R2["h2_prediction"]["anon"]["coef"],
     R2["h2_prediction"]["anon"]["coef"] / R2["h2_prediction"]["anon"]["t"], C["alt"]),
    ("H2: LM dictionary", R2["h2_prediction"]["lm_dict"]["coef"],
     R2["h2_prediction"]["lm_dict"]["coef"] / R2["h2_prediction"]["lm_dict"]["t"], C["grey"]),
    ("H4: price-language headlines", R2["h4_echo"]["priced_any"]["coef"],
     R2["h4_echo"]["priced_any"]["coef"] / R2["h4_echo"]["priced_any"]["t"], C["neg"]),
    ("H4: clean headlines", R2["h4_echo"]["clean"]["coef"],
     R2["h4_echo"]["clean"]["coef"] / R2["h4_echo"]["clean"]["t"], C["pos"]),
]
fig, ax = plt.subplots(figsize=(7.8, 3.6), constrained_layout=True)
ys = np.arange(len(rows))[::-1]
for y, (lab, b, se, c) in zip(ys, rows):
    ax.errorbar(b, y, xerr=1.96 * se, fmt="o", color=c, capsize=3, ms=5)
    tstat = b / se
    ax.annotate(f"$t$={tstat:.2f}", xy=(b, y + 0.18), ha="center", fontsize=8, color=c)
ax.axvline(0, color="black", lw=0.9)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.set_xlabel("coefficient on sentiment (next-day return, per unit of $[-1,1]$ score)")
ax.set_xlim(-0.09, 0.09)
fig.savefig(f"{OUT}/fig_forest.png")
plt.close(fig)

# ---------------- Fig 4: echo decomposition ----------------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.4), constrained_layout=True)
ax = axes[0]
groups = ["same-day\n(named)", "same-day\n(anon)", "next-day\n(named)", "next-day\n(anon)"]
coefsd = [R2["h4_echo"]["same_day_named"]["coef"], R2["h4_echo"]["same_day_anon"]["coef"],
          R2["h1_baseline"]["coef"], R2["h2_prediction"]["anon"]["coef"]]
tvals = [R2["h4_echo"]["same_day_named"]["t"], R2["h4_echo"]["same_day_anon"]["t"],
         R2["h1_baseline"]["t"], R2["h2_prediction"]["anon"]["t"]]
cols = [C["main"], C["alt"], C["main"], C["alt"]]
x = np.arange(4)
bars = ax.bar(x, [c * 100 for c in coefsd], color=cols, alpha=0.85, width=0.62)
for xi, (b, tv) in zip(x, zip(coefsd, tvals)):
    ax.annotate(f"$t$={tv:.2f}", xy=(xi, b * 100 + 0.12), ha="center", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels(groups, fontsize=8.5)
ax.set_ylabel("coefficient (bps per unit sentiment)")
ax = axes[1]
labs = ["price-language\nheadlines (n=38)", "clean headlines\n(n=167)"]
vals = [R2["h4_echo"]["priced_any"]["coef"] * 100, R2["h4_echo"]["clean"]["coef"] * 100]
ts = [R2["h4_echo"]["priced_any"]["t"], R2["h4_echo"]["clean"]["t"]]
bars = ax.bar(np.arange(2), vals, color=[C["neg"], C["pos"]], alpha=0.85, width=0.5)
for xi, (v, tv) in zip(np.arange(2), zip(vals, ts)):
    ax.annotate(f"$t$={tv:.2f}", xy=(xi, v + 0.15), ha="center", fontsize=8.5)
ax.set_xticks(np.arange(2)); ax.set_xticklabels(labs, fontsize=8.5)
ax.set_ylabel("coefficient (bps per unit sentiment)")
ax.axhline(0, color="black", lw=0.8)
diff = R2["h4_echo"]["priced_minus_clean_boot"]
ax.annotate("bootstrap difference:\n%.1f bps, 95%% CI [%.1f, %.1f], p=%.2f"
            % (diff["obs"] * 100, diff["boot_ci95"][0] * 100, diff["boot_ci95"][1] * 100, diff["boot_p"]),
            xy=(0.03, 0.93), xycoords="axes fraction", va="top", fontsize=8, color=C["grey"])
fig.savefig(f"{OUT}/fig_echo.png")
plt.close(fig)

# ---------------- Fig 5: coverage selection ----------------
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
# v4: use the H5 analysis definition (relevance>=30 firm-days, 240 cells)
panel["has_news"] = panel["llm_sent_rel"].notna()
cov = panel.dropna(subset=["ret"])
a1 = cov.loc[cov["has_news"], "ret"].abs() * 1e4
a0 = cov.loc[~cov["has_news"], "ret"].abs() * 1e4
fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.3), constrained_layout=True)
ax = axes[0]
bp = ax.boxplot([a0.values, a1.values], patch_artist=True, widths=0.5,
                labels=[f"no-news firm-days\n(n={len(a0):,})", f"news firm-days\n(n={len(a1):,})"],
                medianprops=dict(color="black", lw=1.2))
for patch, c in zip(bp["boxes"], [C["grey"], C["main"]]):
    patch.set_facecolor(c); patch.set_alpha(0.55)
ax.set_ylabel("|same-day return| (bps)")
ax.annotate(f"means: {a0.mean():.0f} vs {a1.mean():.0f} bps\nfirm+day FE t = {R2['h5_selection']['fe2_t']:.2f} (two-way cl.)",
            xy=(0.03, 0.93), xycoords="axes fraction", va="top", fontsize=8.5, color=C["grey"])
ax = axes[1]
# ECDF
for v, c, lab in [(a0, C["grey"], "no-news"), (a1, C["main"], "news")]:
    xs = np.sort(v.values); ys_ = np.arange(1, len(xs) + 1) / len(xs)
    ax.plot(xs, ys_, color=c, lw=1.5, label=lab)
ax.set_xlabel("|same-day return| (bps)"); ax.set_ylabel("ECDF")
ax.legend(frameon=False)
ax.set_xlim(0, 900)
fig.savefig(f"{OUT}/fig_selection.png")
plt.close(fig)

# ---------------- Fig 6: heterogeneity interactions ----------------
inter = R2["heterogeneity_interactions"]
v1 = R1["heterogeneity"]
fig, ax = plt.subplots(figsize=(7.6, 3.2), constrained_layout=True)
labels = ["size (large)", "news intensity", "volatility regime"]
t_new = [inter["size"]["interaction_t"], inter["news"]["interaction_t"], inter["vol"]["interaction_t"]]
x = np.arange(3)
ax.bar(x - 0.18, [2.51, 2.28, 2.49], width=0.34, color=C["grey"], alpha=0.6, label="v1: split-sample t (upper panel only)")
ax.bar(x + 0.18, t_new, width=0.34, color=C["main"], alpha=0.85, label="v2: interaction-term t (formal test)")
ax.axhline(1.96, color=C["neg"], lw=0.9, ls="--")
ax.annotate("t = 1.96", xy=(2.42, 2.05), fontsize=8, color=C["neg"])
ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel("$t$-statistic")
ax.legend(frameon=False, fontsize=8.2, loc="upper right")
fig.savefig(f"{OUT}/fig_heterogeneity_v2.png")
plt.close(fig)

print("figures v2 saved")
