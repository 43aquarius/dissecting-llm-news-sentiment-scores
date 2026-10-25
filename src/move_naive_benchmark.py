#!/usr/bin/env python3
"""Move the naive two-session benchmark paragraph from results.tex §5.2 to
appendix.tex (app:session), leaving a compact bridge in the main text.
User directive (Layer 1): move revision-log-style narrative to the protocol
appendix; keep only the definitive interleaved design + session-5 conclusions
in the main text."""
import re

RES = "/home/z/my-project/paper/sections/results.tex"
APP = "/home/z/my-project/paper/sections/appendix.tex"

with open(RES) as f:
    res_lines = f.readlines()

# 1. locate the naive-benchmark paragraph line
idx = None
for i, ln in enumerate(res_lines):
    if ln.startswith("\\emph{The naive two-session benchmark it supersedes.}"):
        idx = i
        break
assert idx is not None, "naive benchmark paragraph not found"
para = res_lines[idx].rstrip("\n")

BRIDGE = (
    "\\emph{The superseded two-session benchmark.} The interleaved design exists because the original "
    "fielding~---named scores from 2026-10-15 against anonymized scores fielded twelve hours later~---read "
    "as a $+4.75$-point identity prior (paired $t=5.14$, $p<10^{-6}$), and the staged sessions then unraveled "
    "that reading: the named protocol itself drifted $+5.79$ points between the sittings, itself mostly batch "
    "composition, and the same-session residual~---a one-point displacement whose significance depended on "
    "the test and on the ticker-V exclusion~---was a range, not a verdict, which the interleaved design "
    "resolved at $-2.82$, opposite in sign to the naive shift. The full anatomy of the superseded benchmark"
    "~---distributional agreement, displacement magnitudes, the exact additive decomposition, and the "
    "V-exclusion refinement~---is archived in Appendix~\\ref{app:session} rather than carried in the main "
    "text, so the definitive interleaved estimate and its controls remain the only identity numbers a "
    "reader of the results must retain. Figure~\\ref{fig:distna} shows why the naive reading was tempting, "
    "and Figure~\\ref{fig:session} displays the full anatomy. The protocol lesson is general: condition "
    "contrasts fielded in separate sittings absorb session-level drift, and only same-session interleaving "
    "identifies the contrast the design intends.\n"
)

res_lines[idx] = BRIDGE
with open(RES, "w") as f:
    f.writelines(res_lines)

# 2. adapt the paragraph for the appendix and insert it at the end of app:session
ARCHIVED = para.replace(
    "\\emph{The naive two-session benchmark it supersedes.} The interleaved design exists because the original contrast",
    "\\emph{The naive two-session benchmark, archived in full.} The original contrast that Section~\\ref{sec:results:h2} supersedes",
)
# strip the two main-text figure pointers sentence from the archived copy (figures live in main text)
ARCHIVED = re.sub(
    r"Figure~\\ref\{fig:distna\} shows why the naive reading was tempting, and Figure~\\ref\{fig:session\} displays the full anatomy\. ",
    "",
    ARCHIVED,
)

with open(APP) as f:
    app_text = f.read()

anchor = "\\section{The Interleaved Replication Session}\\label{app:interleaved}"
assert anchor in app_text, "appendix anchor not found"
app_text = app_text.replace(anchor, ARCHIVED + "\n\n" + anchor, 1)

with open(APP, "w") as f:
    f.write(app_text)

print("moved paragraph chars:", len(para))
print("bridge chars:", len(BRIDGE))
print("archived chars:", len(ARCHIVED))
print("OK")
