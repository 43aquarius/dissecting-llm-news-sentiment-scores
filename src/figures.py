#!/usr/bin/env python3
"""Generate paper figures (charts.md compliant: no top/right spines, dashed grid,
no internal titles - LaTeX captions serve as titles, frameless legends)."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA = "/home/z/my-project/data"
OUT = "/home/z/my-project/data/figures"
import os
os.makedirs(OUT, exist_ok=True)

NAVY = "#1F3A5F"
STEEL = "#4A90C4"
SAND = "#8B7E5A"
RED = "#B85C5C"
GRAY = "#8A99A8"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Liberation Serif", "DejaVu Serif"],
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#666666",
    "axes.linewidth": 0.8,
    "xtick.color": "#444444",
    "ytick.color": "#444444",
    "axes.labelcolor": "#222222",
    "grid.linestyle": "--",
    "grid.linewidth": 0.5,
    "grid.alpha": 0.25,
    "legend.frameon": False,
    "figure.dpi": 200,
})

panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
results = json.load(open(f"{DATA}/results.json"))

# ============ Fig 2: daily mean sentiment vs market return ============
news = panel[panel["sent_rel"].notna()] if "sent_rel" in panel else panel[panel["llm_sent_rel"].notna()]
news = panel[panel["llm_sent_rel"].notna()].copy()
news["sent"] = news["llm_sent_rel"] / 100.0
daily_sent = news.groupby("date")["sent"].agg(["mean", "count"]).reset_index()
daily_mkt = panel.groupby("date")["ret"].mean().reset_index()

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 4.8), sharex=True,
                               gridspec_kw={"height_ratios": [1.2, 1]})
ax1.plot(daily_sent["date"], daily_sent["mean"], color=STEEL, lw=2.0)
ax1.fill_between(daily_sent["date"], daily_sent["mean"],
                 daily_sent["mean"].min(), color=STEEL, alpha=0.12)
ax1.axhline(0, color="#999999", lw=0.7, ls=":")
ax1.set_ylabel("Daily mean LLM sentiment")
ax1.grid(axis="y")
ax1.set_ylim(-0.55, 0.75)

ax2.bar(daily_mkt["date"], daily_mkt["ret"] * 100, color=[RED if v < 0 else NAVY for v in daily_mkt["ret"]],
        width=1.8, alpha=0.85)
ax2.set_ylabel("Market return (%)")
ax2.set_xlabel("Date (2026)")
ax2.grid(axis="y")
ax2.axhline(0, color="#999999", lw=0.7)
ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
for label in ax2.get_xticklabels():
    label.set_rotation(0)
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_sentiment_ts.png", bbox_inches=None)
plt.close(fig)

# ============ Fig 3: sentiment distributions LLM vs LM ============
arts = pd.read_json(f"{DATA}/news_all.json")
sc = json.load(open(f"{DATA}/llm_scores.json"))
arts["s"] = arts["url"].map(lambda u: sc.get(u, {}).get("sentiment"))
arts["lm"] = arts["lm_tone"] if "lm_tone" in arts else np.nan
arts_scored = json.load(open(f"{DATA}/news_scored.json"))
df = pd.DataFrame(arts_scored)

fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.4))
axes[0].hist(arts["s"].dropna(), bins=np.arange(-100, 105, 10), color=STEEL,
             edgecolor="white", linewidth=0.6, alpha=0.9)
axes[0].set_xlabel("LLM sentiment score")
axes[0].set_ylabel("Number of headlines")
axes[0].grid(axis="y")
axes[0].axvline(0, color="#555555", lw=0.8, ls=":")

axes[1].hist(df["lm_tone"].dropna(), bins=np.arange(-15, 22, 1.5), color=SAND,
             edgecolor="white", linewidth=0.6, alpha=0.9)
axes[1].set_xlabel("LM dictionary tone (per 100 words)")
axes[1].set_ylabel("Number of headlines")
axes[1].grid(axis="y")
axes[1].axvline(0, color="#555555", lw=0.8, ls=":")
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_dist.png")
plt.close(fig)

# ============ Fig 4: quintile portfolios ============
q_llm = {int(k): v for k, v in results["portfolios"]["by_quintile_mean_bps"].items()}
q_lm = {int(k): v for k, v in results["portfolios"]["lm_by_quintile_bps"].items()}
qs = sorted(q_llm.keys())
fig, ax = plt.subplots(figsize=(8.0, 3.8))
x = np.arange(len(qs))
w = 0.36
b1 = ax.bar(x - w/2, [q_llm[q] for q in qs], w, color=STEEL, label="LLM sentiment", edgecolor="white", lw=0.5)
b2 = ax.bar(x + w/2, [q_lm.get(q, 0) for q in qs], w, color=SAND, label="LM dictionary tone", edgecolor="white", lw=0.5)
ax.axhline(0, color="#555555", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels([f"Q{q}" for q in qs])
ax.set_xlabel("Sentiment quintile (Q1 = most negative, Q5 = most positive)")
ax.set_ylabel("Next-day return (bps)")
ax.grid(axis="y")
ax.legend(loc="upper left", ncol=2)
for rect, v in zip(b1, [q_llm[q] for q in qs]):
    ax.text(rect.get_x() + rect.get_width()/2, v + (3 if v >= 0 else -10),
            f"{v:+.0f}", ha="center", fontsize=9, color=NAVY)
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_quintiles.png")
plt.close(fig)

# ============ Fig 5: horizon coefficients with 95% CI ============
regs = results["regressions"]
hor = results["horizons"]
specs = [
    ("Same day\n($t$)", regs["same_day"]["coef"], regs["same_day"]["se"]),
    ("$t+1$", regs["controls"]["coef"], regs["controls"]["se"]),
    ("$t+2$", hor["fwd2"]["coef"], hor["fwd2"].get("se", np.nan)),
    ("$t+3$", hor["fwd3"]["coef"], hor["fwd3"].get("se", np.nan)),
]
# recompute SEs for horizons from t stats
specs[2] = ("$t+2$", hor["fwd2"]["coef"], abs(hor["fwd2"]["coef"]) / abs(hor["fwd2"]["t"]) if hor["fwd2"]["t"] else np.nan)
specs[3] = ("$t+3$", hor["fwd3"]["coef"], abs(hor["fwd3"]["coef"]) / abs(hor["fwd3"]["t"]) if hor["fwd3"]["t"] else np.nan)

fig, ax = plt.subplots(figsize=(7.5, 3.8))
x = np.arange(len(specs))
coefs = [s[1] * 1e4 for s in specs]  # bps per unit sentiment
errs = [1.96 * s[2] * 1e4 for s in specs]
colors = [NAVY if c >= 0 else RED for c in coefs]
ax.bar(x, coefs, 0.5, color=colors, alpha=0.88, edgecolor="white", lw=0.5)
ax.errorbar(x, coefs, yerr=errs, fmt="none", ecolor="#555555", elinewidth=1.1, capsize=4)
ax.axhline(0, color="#555555", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels([s[0] for s in specs])
ax.set_xlabel("Return horizon relative to news date")
ax.set_ylabel("Regression coefficient (bps per unit sentiment)")
ax.grid(axis="y")
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_horizons.png")
plt.close(fig)

# ============ Fig 6: daily IC series ============
ic = pd.Series(results["ic"]["ic_series"], index=pd.to_datetime(results["ic"]["ic_dates"]))
ic_sorted = ic.sort_index()
roll = ic_sorted.rolling(5, min_periods=3).mean()
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(ic_sorted.index, ic_sorted.values, color=[RED if v < 0 else STEEL for v in ic_sorted.values],
       width=1.6, alpha=0.55, label="Daily IC")
ax.plot(roll.index, roll.values, color=NAVY, lw=2.2, label="5-day rolling mean")
ax.axhline(0, color="#555555", lw=0.8)
ax.set_ylabel("Daily information coefficient")
ax.set_xlabel("Date (2026)")
ax.grid(axis="y")
ax.legend(loc="upper left", ncol=2)
ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=2))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_ic.png")
plt.close(fig)

# ============ Fig 7: heterogeneity coefficients ============
het = results["heterogeneity"]
groups = [
    ("Large firms", het.get("size_large", {}).get("coef", np.nan), het.get("size_large", {}).get("t")),
    ("Small firms", het.get("size_small", {}).get("coef", np.nan), het.get("size_small", {}).get("t")),
    ("High-vol regime", het.get("vol_high_vol", {}).get("coef", np.nan), het.get("vol_high_vol", {}).get("t")),
    ("Low-vol regime", het.get("vol_low_vol", {}).get("coef", np.nan), het.get("vol_low_vol", {}).get("t")),
    ("Multi-news days", het.get("news_multi_news", {}).get("coef", np.nan), het.get("news_multi_news", {}).get("t")),
    ("Single-news days", het.get("news_single_news", {}).get("coef", np.nan), het.get("news_single_news", {}).get("t")),
]
fig, ax = plt.subplots(figsize=(8.0, 4.0))
y = np.arange(len(groups))[::-1]
coefs = [g[1] * 1e4 if g[1] is not None else np.nan for g in groups]
ts = [g[2] for g in groups]
errs = [abs(c) / abs(t) * 1.96 if (t and abs(t) > 0.01 and c == c) else np.nan for c, t in zip(coefs, ts)]
colors = [NAVY if (c is not np.nan and c >= 0) else RED for c in coefs]
ax.barh(y, coefs, 0.55, color=colors, alpha=0.88, edgecolor="white", lw=0.5)
ax.errorbar(coefs, y, xerr=errs, fmt="none", ecolor="#555555", elinewidth=1.0, capsize=3)
ax.set_yticks(y)
ax.set_yticklabels([g[0] for g in groups])
ax.set_xlabel("Coefficient on LLM sentiment (bps per unit)")
ax.axvline(0, color="#555555", lw=0.8)
ax.grid(axis="x")
fig.tight_layout(pad=1.2)
fig.savefig(f"{OUT}/fig_heterogeneity.png")
plt.close(fig)

print("figures saved:", sorted(os.listdir(OUT)))
