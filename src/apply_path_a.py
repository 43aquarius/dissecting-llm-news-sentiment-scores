#!/usr/bin/env python3
"""Path A fallback (execute ONLY if session-5 collection cannot complete):
downgrade session-5 mentions from 'executed' to 'pre-registered, archived,
collection in progress' and remove its claims from abstract/conclusion.
Run: python3 scripts/apply_path_a.py
"""
import sys

PROJ = "/home/z/my-project/paper/sections"
edits = []

def sub(fn, old, new):
    s = open(f"{PROJ}/{fn}").read()
    if old not in s:
        print(f"MISS in {fn}: {old[:70]}")
        sys.exit(1)
    edits.append((fn, s.replace(old, new, 1)))

# 1. abstract: drop swap/temp0 from the condition list
sub("titleblock.tex",
    "scored by GLM-4-Plus under conditions that each vary one ingredient: firm identity visible, removed, or swapped to another firm; independent repeat calls; controlled batch composition; temperature-zero decoding; and the Loughran--McDonald dictionary.",
    "scored by GLM-4-Plus under conditions that each vary one ingredient: firm identity visible or removed; independent repeat calls; controlled batch composition; and the Loughran--McDonald dictionary.")

# 2. declarations: drop the session-5 contrast clause
sub("titleblock.tex",
    "later confirmatory contrasts (identity, batch composition, draw stability, identity-swap and decoding controls) were each pre-specified in archived design documents before their data collection and are reported outside the family and labeled as such",
    "later confirmatory contrasts (identity, batch composition, draw stability) were each pre-specified in archived design documents before their data collection and are reported outside the family and labeled as such")

# 3. data.tex: remove the executed-fifth-sitting sentence, keep sessions 3-4
sub("data.tex",
    " A fifth sitting (2026-10-19), pre-specified in the same staged manner, added the controls that isolate what the identity contrast actually varies: a corrected anonymization pass (the alias table now covers the ticker-V identifiers disclosed in Appendix~\\ref{app:anon}, a deterministic sentence-case smoother, and a forced verification asserting that no focal-firm identifier survives in any anonymized text), an \\emph{identity-swap} pass (each headline's focal identifiers replaced by a seeded random other firm's identifiers, so the text remains a natural company headline but names the wrong company), a \\emph{neutral-prefix} pass (the corrected anonymized text under a ``[Company X]'' prefix, holding the prefix format constant while removing identity content), and two named passes at \\texttt{temperature}$\\,=0$ (decoding-determinism control; Section~\\ref{sec:results:h3}).",
    " A fifth sitting, pre-specified in the same staged manner with falsifiable predictions registered in advance (identity-swap, neutral-prefix, corrected-anonymization, and temperature-0 decoding controls), was interrupted by provider rate-limiting partway through collection; its design document, transformation code, verification report, and partial artifacts are archived in the replication package, and completing it requires no design changes (Section~\\ref{sec:robust:threats}).")

# 4. conclusion: drop the session-5 clause
sub("conclusion.tex",
    "scored under conditions that each vary one ingredient of the measurement and then re-scored in pre-specified staged sessions (interleaved, composition-controlled, and~---in the final sitting~---identity-swapped, prefix-controlled, and decoding-controlled)",
    "scored under conditions that each vary one ingredient of the measurement and then re-scored in pre-specified staged sessions (interleaved and composition-controlled)")

# 5. appendix: replace the session-5 section with a short archived-design note
s = open(f"{PROJ}/appendix.tex").read()
start = s.index("\\section{Session 5: Identity-Swap, Neutral-Prefix, and Decoding Controls}\\label{app:session5}")
end = s.index("\\section{Classification Audit of the Price-Language Flag}")
repl = """\\section{Pre-Registered Control Session (Archived Design)}\\label{app:session5}

A fifth sitting~---identity-swap (each headline's focal identifiers replaced by a seeded random other firm's identifiers, so the text remains a natural company headline but names the wrong company), neutral prefix (``[Company X]'' over the corrected anonymized text), corrected anonymization (the alias table now covers the ticker-V identifiers of Appendix~\\ref{app:anon}; a forced verification pass reports zero residual focal identifiers across all transformed texts), and two named passes at \\texttt{temperature}$\\,=0$~---was pre-specified in an archived design document with falsifiable predictions before any of its data was collected (\\texttt{audits/P2\\_preregistration\\_session5.md}). Data collection was interrupted by sustained provider rate-limiting after 63 of the 84 planned calls; the pre-registration, the transformation code (with the seeded swap map and the verification report), the per-call log, and the partial score files are all archived in the replication package, and the collection is resumable without design changes. In keeping with the paper's discipline, no estimate from this sitting is reported until the collection is complete; the pre-registered predictions and the analysis plan are on file for the completed version.

"""
s = s[:start] + repl + s[end:]
open(f"{PROJ}/appendix.tex", "w").write(s)

for fn, content in edits:
    open(f"{PROJ}/{fn}", "w").write(content)
print("Path A applied: session-5 downgraded to pre-registered/archived status")
