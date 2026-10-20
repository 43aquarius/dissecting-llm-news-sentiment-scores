#!/usr/bin/env python3
"""Figures v7: downstream-consequences visualization (companion to Table tab:downstream).

Three panels:
  (A) predictive slope beta across all seven archived named-protocol sources
      with 95% CIs -> the slope is robust to batch composition and re-batching
  (B) firm-day counts above the fixed "+50" threshold by composition ->
      absolute-threshold uses are NOT robust (roughly doubled)
  (C) daily cross-sectional mean sentiment under the two compositions of
      session 3 -> a +4.5-point level shift with 16% day-over-day sign flips

Style matches figures_v5.py (charts.md conventions). Panel A/B numbers are read
from data/results_batch_downstream.json (batch_downstream.py); panel C's daily
series is recomputed from the archived session-3 score files with the same
relevance>=30 firm-day aggregation as batch_downstream.py.

Output: data/figures/fig_downstream.png
"""
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

R = json.load(open(f"{DATA}/results_batch_downstream.json"))
sl = R["slpes"] if "slpes" in R else R["slopes"]
th = R["thresholds_firmday"]

# ---------------- Panel C inputs: recompute daily series (session 3) -------------
# Exact replication of batch_downstream.py's daily_timeseries: firm-day means over
# the REGRESSION sample (ctrl: non-missing ret_fwd1, ret_lag1, vol_21, mkt_ew, ret),
# then daily means, then day-over-day sign comparison on common days.
arts = json.load(open(f"{DATA}/news_scored.json"))
inwin = [a for a in arts if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
url_order = [a["url"] for a in inwin]
def load_sent(path):
    d = json.load(open(path))
    return {u: d[u]["sentiment"] for u in url_order if u in d}
rel = {u: json.load(open(f"{DATA}/llm_scores.json")).get(u, {}).get("relevance") for u in url_order}
rows = [{"ticker": a["ticker"], "date": a["date_iso"], "relevance": rel.get(u), "url": u}
        for a, u in zip(inwin, url_order)]
rdf = pd.DataFrame(rows)
hi = rdf[rdf["relevance"] >= 30].copy()
s3n = {r: load_sent(f"{DATA}/llm_scores_s3_named_r{r}.json") for r in (1, 2, 3, 4)}
hi["sent_s3_named4"] = hi["url"].map({u: float(np.mean([s3n[r][u] for r in (1, 2, 3, 4)])) for u in url_order}) / 100.0
hi["sent_s3_v1c"] = hi["url"].map(load_sent(f"{DATA}/llm_scores_s3_v1comp.json")) / 100.0
agg = hi.groupby(["ticker", "date"]).agg({"sent_s3_named4": "mean", "sent_s3_v1c": "mean"}).reset_index()
agg["date"] = pd.to_datetime(agg["date"])
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
panel["ret_fwd1"] = panel.groupby("ticker")["ret"].shift(-1)
pp = panel.merge(agg, on=["ticker", "date"], how="left")
ctrl = pp[pp["sent_s3_named4"].notna()].drop_duplicates(subset=["ticker", "date_str"])
ctrl = ctrl.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew", "ret"]).copy()
daily = ctrl.groupby("date_str").agg({"sent_s3_named4": "mean", "sent_s3_v1c": "mean"}).reset_index().sort_values("date_str")
daily = daily.dropna(subset=["sent_s3_named4", "sent_s3_v1c"])
d341 = daily["sent_s3_named4"].values * 100.0
d542 = daily["sent_s3_v1c"].values * 100.0
dates = pd.to_datetime(daily["date_str"])
# day-over-day sign flips between the two compositions (as archived)
s341 = np.sign(np.diff(d341))
s542 = np.sign(np.diff(d542))
flip = s341 != s542
flip_rate = flip.mean()
n_flip = int(flip.sum())

# ---------------- Figure ----------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.6), constrained_layout=True)
A, B, P = axes

# Panel A: slopes across sources
order = [("s1_v1", "Sess.1\nnamed"), ("s2_repm", "Sess.2\nrepeats"),
         ("s3_named4", "Sess.3\n341-comp"), ("s3_v1c", "Sess.3\n542-comp"),
         ("s4_orig", "Sess.4\n341-comp"), ("s4_v1c", "Sess.4\n542-comp"),
         ("s4_shuf", "Sess.4\nre-batch")]
comp_col = {"s3_named4": C["main"], "s4_orig": C["main"], "s1_v1": C["grey"],
            "s2_repm": C["grey"], "s3_v1c": C["alt"], "s4_v1c": C["alt"],
            "s4_shuf": C["sand"]}
xs = np.arange(len(order))
for x, (k, lab) in zip(xs, order):
    b, t = sl[k]["beta"], sl[k]["t"]
    se = b / t
    A.errorbar(x, b, yerr=1.96 * abs(se), fmt="o", color=comp_col[k], ms=5,
               capsize=3, lw=1.2, zorder=3)
A.axhline(0, color="k", lw=0.8, zorder=1)
A.set_xticks(xs, [lab for _, lab in order], fontsize=7.6)
A.set_ylabel(r"Predictive coefficient $\hat\beta$ (next-day)")
A.set_ylim(-0.002, 0.024)
A.annotate("slopes robust:\nall compositions overlap", xy=(0.985, 0.03), xycoords="axes fraction",
           ha="right", fontsize=8.2, color=C["pos"])

# Panel B: threshold counts
groups = [("Session 3", th["s3_named4"]["n_ge_pos50"], th["s3_v1c"]["n_ge_pos50"], 22 / 50),
          ("Session 4", th["s4_orig"]["n_ge_pos50"], th["s4_v1c"]["n_ge_pos50"], 27 / 43)]
xg = np.arange(len(groups))
w = 0.34
b1 = B.bar(xg - w / 2, [g[1] for g in groups], w, color=C["main"], label="341-composition")
b2 = B.bar(xg + w / 2, [g[2] for g in groups], w, color=C["alt"], label="542-composition")
for i, g in enumerate(groups):
    B.text(xg[i] - w / 2, g[1] + 1.2, str(g[1]), ha="center", fontsize=8.5)
    B.text(xg[i] + w / 2, g[2] + 1.2, str(g[2]), ha="center", fontsize=8.5)
    B.annotate("", xy=(xg[i] + w / 2, g[2] - 2), xytext=(xg[i] - w / 2, g[1] - 2),
               arrowprops=dict(arrowstyle="->", color=C["neg"], lw=1.1))
    B.text(xg[i], max(g[1], g[2]) + 6.5, f"x{g[2]/g[1]:.1f}", ha="center",
           fontsize=8.5, color=C["neg"])
B.set_xticks(xg, [g[0] for g in groups])
B.set_ylabel(r"Firm-days with score $\geq +50$")
B.set_ylim(0, 62)
B.legend(loc="upper left", fontsize=8, frameon=False)
B.annotate("threshold uses NOT robust:\ntrade count roughly doubles", xy=(0.985, 0.55),
           xycoords="axes fraction", ha="right", fontsize=8.2, color=C["neg"])

# Panel C: daily series
x = np.arange(len(daily))
P.plot(x, d341, color=C["main"], lw=1.5, label="341-composition", zorder=3)
P.plot(x, d542, color=C["alt"], lw=1.5, label="542-composition", zorder=3)
P.fill_between(x, d341, d542, color=C["alt"], alpha=0.12, zorder=2)
# mark days whose day-over-day sign differs between the two series
flip_idx = np.where(flip)[0] + 1
P.scatter(flip_idx, d341[flip_idx], color=C["neg"], s=16, zorder=4,
           label=f"sign-flip day ($n={len(flip_idx)}$)")
P.axhline(0, color="k", lw=0.8, zorder=1)
P.set_ylabel("Daily mean sentiment (points)")
tick = np.linspace(0, len(x) - 1, 5).astype(int)
P.set_xticks(tick, [d.strftime("%b %d") for d in dates.iloc[tick]], fontsize=8)
P.legend(loc="upper right", fontsize=7.6, frameon=False)
P.annotate(f"level shift +{R['daily_timeseries']['s3_v1c_vs_s3_named4']['mean_shift_points']:.1f} pts\n"
           f"{100*flip_rate:.0f}% of day-over-day signs flip",
           xy=(0.02, 0.03), xycoords="axes fraction", fontsize=8.2, color=C["grey"])

fig.savefig(f"{DATA}/figures/fig_downstream.png")
print("saved", f"{DATA}/figures/fig_downstream.png")
print("panel C recomputed: shift",
      f"{np.mean(d542 - d341):+.2f} pts, sign-flip rate {100*flip_rate:.1f}% "
      f"(archived table: 16%)")
