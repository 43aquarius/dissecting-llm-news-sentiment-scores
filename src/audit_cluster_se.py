#!/usr/bin/env python3
"""AUDIT: What does statsmodels cov_type='cluster' with 2D groups actually compute?

Compare on the actual news panel:
  A) statsmodels 2D groups (as used in analysis.py)
  B) manual Cameron-Gelbach-Miller two-way cluster (Froot + sum of one-ways - intersection)
  C) one-way cluster by firm
  D) one-way cluster by day
  E) intersection cluster (firm x day cell)
  F) HC1 robust
"""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

DATA = "/home/z/my-project/data"
panel = pd.read_csv(f"{DATA}/panel.csv", parse_dates=["date"])
panel["date_str"] = panel["date"].dt.strftime("%Y-%m-%d")
panel = panel.sort_values(["ticker", "date"])
for h in (1, 2, 3):
    panel[f"ret_fwd{h}"] = panel.groupby("ticker")["ret"].shift(-h)
panel["sent_rel"] = panel["llm_sent_rel"] / 100.0
panel["lm"] = panel["lm_tone"] / 100.0

news = panel[panel["sent_rel"].notna()].copy()
news = news.drop_duplicates(subset=["ticker", "date_str"]).sort_values(["ticker", "date"])
ctrl = news.dropna(subset=["ret_fwd1", "ret_lag1", "vol_21", "mkt_ew"]).copy()

print(f"n obs: {len(ctrl)}, firms: {ctrl['ticker'].nunique()}, days: {ctrl['date_str'].nunique()}")
# cell sizes: how many obs per (firm, day) intersection cell?
cell_sizes = ctrl.groupby(["ticker", "date_str"]).size()
print(f"obs per (firm,day) cell: max={cell_sizes.max()}, mean={cell_sizes.mean():.3f}")
print(f"cells with >1 obs: {(cell_sizes > 1).sum()} of {len(cell_sizes)}")

# ---- A) statsmodels 2D groups (the analysis.py approach) ----
fcode, fnames = pd.factorize(ctrl["ticker"])
dcode, dnames = pd.factorize(ctrl["date_str"])
groups2d = np.column_stack([fcode, dcode])
resA = smf.ols("ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew", data=ctrl).fit(
    cov_type="cluster", cov_kwds={"groups": groups2d})
seA = resA.bse["sent_rel"]

# ---- manual sandwich helpers ----
X = np.column_stack([
    np.ones(len(ctrl)),
    ctrl["sent_rel"].values,
    ctrl["ret_lag1"].values,
    ctrl["vol_21"].values,
    ctrl["mkt_ew"].values,
])
y = ctrl["ret_fwd1"].values
XtX_inv = np.linalg.inv(X.T @ X)
beta = XtX_inv @ X.T @ y
u = y - X @ beta

def cluster_meat(unit_codes):
    meat = np.zeros((X.shape[1], X.shape[1]))
    for g in np.unique(unit_codes):
        idx = unit_codes == g
        Xg = X[idx]; ug = u[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    return meat

# B) Cameron-Gelbach-Miller two-way: A + B - intersection
meat_firm = cluster_meat(fcode)
meat_day = cluster_meat(dcode)
inter_codes = pd.factorize(list(zip(fcode, dcode)))[0]
meat_inter = cluster_meat(inter_codes)
meat_cgm = meat_firm + meat_day - meat_inter
Vcgm = XtX_inv @ meat_cgm @ XtX_inv
seB = np.sqrt(Vcgm[1, 1])

# C) one-way firm
Vf = XtX_inv @ meat_firm @ XtX_inv
seC = np.sqrt(Vf[1, 1])
# D) one-way day
Vd = XtX_inv @ meat_day @ XtX_inv
seD = np.sqrt(Vd[1, 1])
# E) intersection only
Vi = XtX_inv @ meat_inter @ XtX_inv
seE = np.sqrt(Vi[1, 1])
# F) HC1
resHC = smf.ols("ret_fwd1 ~ sent_rel + ret_lag1 + vol_21 + mkt_ew", data=ctrl).fit(cov_type="HC1")
seF = resHC.bse["sent_rel"]

coef = beta[1]
print(f"\ncoef on sent_rel: {coef:.6f}  (analysis.py/paper: 0.014892)\n")
print(f"A) statsmodels 2D groups          SE={seA:.6f}  t={coef/seA:.3f}")
print(f"B) Cameron-Gelbach-Miller 2-way   SE={seB:.6f}  t={coef/seB:.3f}")
print(f"C) one-way cluster by FIRM        SE={seC:.6f}  t={coef/seC:.3f}")
print(f"D) one-way cluster by DAY         SE={seD:.6f}  t={coef/seD:.3f}")
print(f"E) intersection (firm x day cell) SE={seE:.6f}  t={coef/seE:.3f}")
print(f"F) HC1 heteroskedastic robust     SE={seF:.6f}  t={coef/seF:.3f}")
print(f"\nA == E ?  {np.isclose(seA, seE)}")
print(f"A == B ?  {np.isclose(seA, seB)}")
print(f"A == F ?  {np.isclose(seA, seF)}")
