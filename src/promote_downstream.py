#!/usr/bin/env python3
"""L3-1: promote the downstream-consequences block (paragraph + tab:downstream +
fig:downstream) from appendix.tex (app:interleaved) into results.tex right after
the 'What the drift is made of' paragraph (sec:results:h2), per user directive
'Make Table 12 and Figure 9 more prominent (slopes/ranks robust, thresholds/
time-series not -- visible at a glance)'."""
import re

APP = "/home/z/my-project/paper/sections/appendix.tex"
RES = "/home/z/my-project/paper/sections/results.tex"

app = open(APP).read()
res = open(RES).read()

# 1. extract the block: paragraph at '\\paragraph{Downstream consequences...' through the figure end
start = app.index("\\paragraph{Downstream consequences of the composition effect.}")
end_anchor = "\\section{Session-5 Controls: Archived Design Document and Results}\\label{app:session5}"
end = app.index(end_anchor)
block = app[start:end].rstrip() + "\n"
assert "\\label{tab:downstream}" in block and "\\label{fig:downstream}" in block

# 2. remove from appendix, leave a pointer
pointer = ("The downstream-consequences analysis of the composition effect "
           "(Table~\\ref{tab:downstream} and Figure~\\ref{fig:downstream}) is presented in the main text "
           "(Section~\\ref{sec:results:h2}); the underlying per-source arithmetic is \\texttt{batch\\_downstream.py} "
           "(seed 20261019) over the archived sources of sessions 1--4.\n")
app = app[:start] + pointer + "\n" + app[end:]

# 3. shorten the drift-paragraph closing in results.tex (avoid duplication)
old_close = ("Appendix~\\ref{app:interleaved} traces the consequence downstream: the level shift leaves slopes and "
             "cross-sectional ranks intact ($p>0.9$ for every composition contrast of the predictive coefficient) "
             "but doubles the trade count of a fixed ``score $\\geq +50$'' rule and flips the sign of day-over-day "
             "changes in the daily-mean series on up to a quarter of trading days~---batch composition is harmless "
             "to conditional, cross-sectional uses and disqualifying for absolute-threshold and time-series uses.")
new_close = ("Table~\\ref{tab:downstream} and Figure~\\ref{fig:downstream} trace the consequence downstream and "
             "carry the operational verdict: batch composition is harmless to conditional, cross-sectional uses "
             "and disqualifying for absolute-threshold and time-series uses.")
assert old_close in res, "drift-paragraph closing not found"
res = res.replace(old_close, new_close)

# 4. insert the block after the drift paragraph (before '\emph{Prediction layer.}')
anchor = "\\emph{Prediction layer.} Column (3) of Table~\\ref{tab:core}"
idx = res.index(anchor)
res = res[:idx] + block + "\n" + res[idx:]

open(APP, "w").write(app)
open(RES, "w").write(res)
print("moved block chars:", len(block))
print("appendix pointer installed; results.tex block inserted before Prediction layer")
