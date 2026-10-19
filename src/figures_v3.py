#!/usr/bin/env python3
"""Figures v3 (revision): session-confounding decomposition figure.
Style: charts.md conventions (no top/right spines, dashed grid, no in-figure
titles, constrained_layout) — matches figures_v2.py."""
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

arts = json.load(open(f"{DATA}/news_scored.json"))
orig = json.load(open(f"{DATA}/llm_scores.json"))
anon = json.load(open(f"{DATA}/llm_scores_anon.json"))
reps = {k: json.load(open(f"{DATA}/llm_scores_{k}.json")) for k in ("rep1", "rep2", "rep3")}

rows = []
for a in arts:
    if not (a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"):
        continue
    u = a["url"]
    o = orig.get(u, {}).get("sentiment"); an = anon.get(u, {}).get("sentiment")
    r = [reps[k].get(u, {}).get("sentiment") for k in ("rep1", "rep2", "rep3")]
    if None in (o, an) or None in r:
        continue
    rows.append({"o": o, "an": an, "repm": float(np.mean(r))})
df = pd.DataFrame(rows)
d_sess = df["o"] - df["repm"]      # between-session, same (named) condition
d_id = df["an"] - df["repm"]        # within-session, identity contrast

fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.4), constrained_layout=True)

# ---- Panel A: paired-difference distributions ----
ax = axes[0]
bins = np.arange(-70, 71, 5)
ax.hist(d_sess[np.isfinite(d_sess)], bins=bins, alpha=0.62, color=C["main"],
        density=True, label="named$_{Oct15}$ $-$ named$_{Oct16}$ (session drift)")
ax.hist(d_id[np.isfinite(d_id)], bins=bins, alpha=0.62, color=C["alt"],
        density=True, label="anonymized$_{Oct16}$ $-$ named$_{Oct16}$ (identity)")
ax.axvline(0, color="black", lw=0.8)
ax.axvline(d_sess.mean(), color=C["main"], lw=1.4, ls="--")
ax.axvline(d_id.mean(), color=C["alt"], lw=1.4, ls="--")
ax.set_xlabel("paired score difference (points)")
ax.set_ylabel("density")
ax.legend(frameon=False, loc="upper left", fontsize=8.2)
tt_s = stats.ttest_rel(df["o"], df["repm"]); tt_i = stats.ttest_rel(df["an"], df["repm"])
ax.annotate(f"session drift: {d_sess.mean():+.2f} (t={tt_s.statistic:.2f})",
            xy=(0.02, 0.90), xycoords="axes fraction", fontsize=8.2, color=C["main"])
ax.annotate(f"same-session identity: {d_id.mean():+.2f} (t={tt_i.statistic:.2f}, p={tt_i.pvalue:.2f})",
            xy=(0.02, 0.81), xycoords="axes fraction", fontsize=8.2, color=C["alt"])

# ---- Panel B: decomposition forest ----
ax = axes[1]
def ci_paired(x):
    se = x.std(ddof=1) / np.sqrt(len(x))
    return x.mean() - 1.96 * se, x.mean() + 1.96 * se
est = [
    ("published shift\n(named$_{Oct15}$ $-$ anon$_{Oct16}$)", 4.751, *ci_paired(df["o"] - df["an"]), C["neg"]),
    ("session drift\n(named$_{Oct15}$ $-$ named$_{Oct16}$)", 5.792, *ci_paired(df["o"] - df["repm"]), C["main"]),
    ("same-session identity\n(named$_{Oct16}$ $-$ anon$_{Oct16}$)", -1.041, *ci_paired(df["repm"] - df["an"]), C["alt"]),
]
ypos = np.arange(len(est))[::-1]
for y, (lab, m, lo, hi, col) in zip(ypos, est):
    ax.plot([lo, hi], [y, y], color=col, lw=2.2, solid_capstyle="round")
    ax.plot(m, y, "o", color=col, ms=6)
    ax.annotate(f"{m:+.2f}  [{lo:+.2f}, {hi:+.2f}]", xy=(hi, y), xytext=(6, 0),
                textcoords="offset points", va="center", fontsize=8.2, color=col)
ax.axvline(0, color="black", lw=0.9)
ax.set_yticks(ypos)
ax.set_yticklabels([e[0] for e in est], fontsize=8.6)
ax.set_xlabel("score points (named $-$ anonymized direction)")
ax.set_xlim(-6, 11.5)

fig.savefig(f"{DATA}/figures/fig_session.png")
print(f"saved {DATA}/figures/fig_session.png  (n={len(df)} articles)")
