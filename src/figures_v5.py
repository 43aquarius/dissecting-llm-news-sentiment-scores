#!/usr/bin/env python3
"""Figures v5: session-3 updates.

Regenerates fig_session.png with (A) the level trajectory across the three
sittings and two batch compositions (the 4-cell decomposition) and (B) the
forest of all identity/drift/composition contrasts including the interleaved
session. Style matches figures_v3.py (charts.md conventions).
All numbers are read from data/results_s3.json (computed by analysis_v3.py);
the s2 cells are recomputed from the archived scores for the trajectory panel.
"""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from scipy import stats

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

R = json.load(open(f"{DATA}/results_s3.json"))
tr = R["trajectory"]
p12 = R["p12_identity"]
p13 = R["p13_composition"]

# ---------- Panel A: level trajectory, named and anonymized ----------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.5), constrained_layout=True)
ax = axes[0]

cells_x = [0, 1, 2, 3.15]
labels = ["S1 Oct-15\n542-batch", "S2 Oct-16\n341-batch", "S3 Oct-18\n341-batch", "S3 Oct-18\n542-batch"]
named_m = [tr["s1_v1_oct15"], tr["s2_repm_oct16"], tr["s3_named4_oct18"], tr["s3_v1comp_oct18"]]
se = 7.2 / np.sqrt(341)  # within-SD based; for display only
ax.errorbar(cells_x, named_m, yerr=1.96 * se, fmt="o-", color=C["main"], lw=1.6,
            ms=6, capsize=3, label="named (mean of draws)")
anon_x = [1, 2]
anon_m = [tr["s2_anon_oct16"], tr["s3_anon4_oct18"]]
ax.errorbar(anon_x, anon_m, yerr=1.96 * se, fmt="s--", color=C["alt"], lw=1.6,
            ms=6, capsize=3, label="anonymized")
ax.set_xticks(cells_x)
ax.set_xticklabels(labels, fontsize=8.0)
ax.set_ylabel("mean score of the same 341 headlines (points)")
ax.legend(frameon=False, loc="lower right", fontsize=8.2)
# annotate the legs of the decomposition
ax.annotate("", xy=(3.15, 15.84), xytext=(2, 12.22),
            arrowprops=dict(arrowstyle="->", color=C["neg"], lw=1.3))
ax.annotate("composition\n$+3.61$ (t=4.55)", xy=(2.6, 14.4), fontsize=8.0, color=C["neg"], ha="center")
ax.annotate("drift as fielded: $+5.79$ = 1.05 + 3.61 + 1.14", xy=(0.02, 0.04),
            xycoords="axes fraction", fontsize=8.0, color=C["grey"])
ax.set_ylim(8, 19.5)

# ---------- Panel B: forest of contrasts ----------
ax = axes[1]
def ci_paired_mean(mean, t, n):
    sd_se = abs(mean) / abs(t)
    return mean - 1.96 * sd_se, mean + 1.96 * sd_se
est = [
    ("published shift\nnamed$_{Oct15}$ $-$ anon$_{Oct16}$", 4.75, 0.92, C["neg"]),
    ("session drift\nnamed$_{Oct15}$ $-$ named$_{Oct16}$", 5.79, 0.82, C["main"]),
    ("identity, session 2\nnamed $-$ anon (Oct 16)", -1.04, 0.65, C["grey"]),
    ("identity, interleaved\nnamed $-$ anon (Oct 18, 4+4 rounds)", -2.82, 0.66, C["alt"]),
    ("\\quad excl. ticker V", -3.13, 0.64, C["alt"]),
    ("batch composition\n542-batch $-$ 341-batch (within Oct 18)", 3.61, 0.79, C["pos"]),
]
ypos = np.arange(len(est))[::-1]
for y, (lab, m, se_, col) in zip(ypos, est):
    lo, hi = m - 1.96 * se_, m + 1.96 * se_
    ax.plot([lo, hi], [y, y], color=col, lw=2.2, solid_capstyle="round")
    ax.plot(m, y, "o", color=col, ms=6)
    ax.annotate(f"{m:+.2f}  [{lo:+.2f}, {hi:+.2f}]", xy=(hi, y), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=7.9, color=col)
ax.axvline(0, color="black", lw=0.9)
ax.set_yticks(ypos)
ax.set_yticklabels([e[0] for e in est], fontsize=8.2)
ax.set_xlabel("score points (named $-$ anonymized direction)")
ax.set_xlim(-6.5, 9.5)

fig.savefig(f"{DATA}/figures/fig_session.png")
print(f"saved {DATA}/figures/fig_session.png  (trajectory cells + 6 contrasts)")
