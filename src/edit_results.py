#!/usr/bin/env python3
"""Apply results.tex revision edits via span replacement (robust to unicode nuances)."""
import re

P = "/home/z/my-project/paper/sections/results.tex"
t = open(P).read()
orig = t
def span_replace(text, start_marker, end_marker, new, include_end=True):
    i = text.find(start_marker)
    assert i != -1, f"start not found: {start_marker[:60]!r}"
    j = text.find(end_marker, i)
    assert j != -1, f"end not found: {end_marker[:60]!r}"
    j = j + len(end_marker) if include_end else j
    return text[:i] + new + text[j:]

# ---- R1: power sentence in 5.1 (skip if already applied) ----
if "app:power" not in t:
    t = t.replace(
        "in a 205-observation sample}. We flag that the earlier draft",
        "in a 205-observation sample}. The design's resolution is similarly bounded: "
        "at 80\\% power, the minimum detectable next-day coefficient is $0.020$~---"
        "one-third larger than the estimate itself~---and the power of the test "
        "against the observed effect is $0.56$ (Appendix~\\ref{app:power}). "
        "We flag that the earlier draft")
    assert "app:power" in t, "R1 failed"

# ---- R2: rewrite the measurement-layer paragraph (span) ----
new_ml = (
 "\\emph{Measurement layer.} On the identical 341 headlines, named scores exceed anonymized "
 "scores by 4.75 points on average (paired $t=5.14$, $p<10^{-6}$). The two distributions correlate "
 "at $0.900$ (Pearson; Spearman $0.888$); 43.4\\% of headlines receive the identical score in both "
 "conditions, and the mean absolute difference is 11.2 points. This is what the audit originally "
 "reported as an identity prior, and it is what the revision re-opens. The two conditions were not "
 "fielded in the same sitting: the original named round ran on 2026-10-15 (16:01--16:24 UTC), while "
 "the anonymized round and all three named repeats ran in a single 2026-10-16 sitting "
 "(04:24--04:33 UTC), roughly twelve hours later, under a protocol that is verbatim-identical for "
 "the named conditions (same system prompt, same user-message format, same batch size). The named "
 "protocol itself drifted $+5.79$ points in level between the two sittings (paired $t=7.03$, "
 "$p<10^{-11}$): the same prompts, the same headlines, twelve hours apart, score six points more "
 "bullish in the first sitting. Benchmarked within session, the identity level effect is $-1.04$ "
 "points in the named-minus-anonymized direction~---anonymized scores sit, insignificantly, "
 "\\emph{above} their same-session named twins ($t=1.60$, $p=0.11$; Wilcoxon $p=0.04$; against the "
 "three repeats individually, $+1.30$, $+1.67$, and $+0.15$ in the anonymized direction, one of "
 "three below 0.05). The published shift decomposes exactly: $+4.75 = +5.79$ (session drift) "
 "$- 1.04$ (same-session identity). Figure~\\ref{fig:session} displays the decomposition. We "
 "accordingly retract the interpretation of the $+4.75$ shift as a firm-specific prior: on this "
 "corpus, the scorer's apparent optimism about known firms is predominantly the scoring process "
 "moving between sittings, and the earlier framing of the shift as the out-of-sample analog of "
 "\\citet{glasserman2023}'s distraction effect was an artifact of session scheduling. What survives "
 "is a protocol lesson with teeth: condition contrasts fielded in separate sittings absorb "
 "session-level drift, and only same-session interleaving identifies the contrast the design "
 "intends. The dispersion benchmarks agree with the level evidence: within the October-16 sitting, "
 "anonymized-versus-named displacement (7.9 points of mean absolute difference) exceeds "
 "repeat-versus-repeat displacement (6.5 points) by roughly the same one-point margin as the level "
 "shift, while the cross-session displacement (11.3 points) towers over both.")
t = span_replace(t, "\\emph{Measurement layer.}", "exclusively mega-caps.", new_ml)

# ---- R3: figure caption update + insert fig_session + prediction layer sentences ----
t = t.replace(
    "\\includegraphics[width=0.95\\textwidth]{../data/figures/fig_scores_named_anon.png}\n"
    "\\caption{Named versus anonymized score distributions on the identical 341 headlines. Left: "
    "overlapping histograms (the named distribution sits to the right). Right: histogram of paired "
    "differences, with the mean shift of $+4.75$ marked.}",
    "\\includegraphics[width=0.95\\textwidth]{../data/figures/fig_scores_named_anon.png}\n"
    "\\caption{Named versus anonymized score distributions on the identical 341 headlines. Left: "
    "overlapping histograms (the named distribution sits to the right). Right: histogram of paired "
    "differences, with the mean shift of $+4.75$ marked. Both panels contrast the October-15 named "
    "round with the October-16 anonymized round and therefore mix identity with session drift; see "
    "Figure~\\ref{fig:session}.}")

fig_session = (
 "\\begin{figure}[htbp]\n\\centering\n"
 "\\includegraphics[width=\\textwidth]{../data/figures/fig_session.png}\n"
 "\\caption{Decomposition of the apparent identity shift. Left: article-level paired-difference "
 "distributions for the between-session drift (named$_{\\text{Oct 15}}-$ named$_{\\text{Oct 16}}$) "
 "and the within-session identity contrast (anonymized$_{\\text{Oct 16}}-$ named$_{\\text{Oct 16}}$). "
 "Right: point estimates with 95\\% CIs~---the published cross-session shift ($+4.75$) is dominated "
 "by the session drift ($+5.79$); the same-session identity component ($-1.04$) is indistinguishable "
 "from zero.}\n\\label{fig:session}\n\\end{figure}\n")
# insert after the distna figure block
i = t.find("\\label{fig:distna}\n\\end{figure}\n")
assert i != -1, "distna block not found"
i += len("\\label{fig:distna}\n\\end{figure}\n")
t = t[:i] + "\n" + fig_session + t[i:]

t = t.replace(
    "the two conditions are statistically indistinguishable as predictors. "
    "The named-versus-dictionary difference is likewise insignificant",
    "the two conditions are statistically indistinguishable as predictors. Because that comparison "
    "pairs an October-15 named score with an October-16 anonymized score, we re-run it entirely "
    "inside the October-16 sitting: the anonymized aggregate gives $0.0144$ ($t=1.78$) against "
    "$0.0147$ ($t=1.87$) for the mean of the three same-session named repeats, difference $0.0002$ "
    "(day-cluster bootstrap $p=0.905$). The prediction-layer conclusion~---identity does not change "
    "predictive content~---is robust to the session benchmark on both layers of the comparison. "
    "The named-versus-dictionary difference is likewise insignificant")

# ---- R4: two-layer synthesis sentence ----
t = span_replace(t,
    "The two-layer result is the paper's cleanest inference",
    "as a predictive difference, and does not.",
    "The two-layer result is the paper's cleanest inference about what the model brings to the "
    "text~---now with the level channel corrected by its own revision: identity neither moves the "
    "score once conditions are benchmarked within a session, nor moves the signal in any comparison. "
    "A prior that inflated all of a firm's headlines equally would be differenced out of any "
    "predictive regression that conditions on the firm; a prior that differentially tracked which "
    "headlines \\emph{matter} would have shown up as a predictive difference, and does not. The "
    "level evidence that initially pointed the other way turned out to measure the session, not "
    "the prior.")

# ---- R5: H3 session decomposition ----
t = t.replace(
    "mean within-headline standard deviation is 7.8 points (Figure~\\ref{fig:reliability}). "
    "Reliability of $0.92$ is high",
    "mean within-headline standard deviation is 7.8 points (Figure~\\ref{fig:reliability}). "
    "The four calls, however, span two sittings: the three October-16 draws alone yield "
    "$\\text{ICC}(2,3)=0.949$, so pooling across the twelve-hour gap costs three reliability "
    "points. The pooled number is the right one to report for a production pipeline~---"
    "single-sitting ICCs overstate what re-scoring tomorrow will deliver~---and the same pooling "
    "is why the published ICC already prices in the session drift documented in "
    "Section~\\ref{sec:results:h2}. Reliability of $0.92$ is high")

# ---- R6: tab:diff rows + notes ----
t = span_replace(t,
    "$\\beta_{\\text{named}}-\\beta_{\\text{anonymized}}$ & 0.0004",
    "all cross-instrument statements are direct difference tests.\n\\end{tablenotes}",
    "$\\beta_{\\text{named}}-\\beta_{\\text{anonymized}}$ (cross-session) & 0.0004 & "
    "$[-0.0044,\\ 0.0045]$ & 0.887 \\\\\n"
    "$\\beta_{\\text{named}}-\\beta_{\\text{anonymized}}$ (same session, Oct 16) & 0.0002 & "
    "$[-0.0034,\\ 0.0037]$ & 0.905 \\\\\n"
    "$\\beta_{\\text{named}}-\\beta_{\\text{dictionary}}$ & $-$0.0119 & $[-0.0737,\\ 0.0576]$ & 0.731 \\\\\n"
    "$\\beta_{\\text{price-lang.}}-\\beta_{\\text{clean}}$ & 0.0436 & $[-0.0016,\\ 0.0864]$ & 0.077 \\\\\n"
    "Level shift, cross-session (named Oct 15 $-$ anonymized Oct 16, points) & $+$4.75 &~--- & $<$0.0001 \\\\\n"
    "Session drift (named Oct 15 $-$ named Oct 16, points) & $+$5.79 &~--- & $<$0.0001 \\\\\n"
    "Identity level shift, same session (named $-$ anonymized, Oct 16, points) & $-$1.04 & "
    "$[-2.32,\\ +0.23]$ & 0.111 \\\\\n"
    "\\bottomrule\n\\end{tabular}\n"
    "\\begin{tablenotes}[flushleft]\\footnotesize\n"
    "\\item Differences of next-day predictive coefficients from Table~\\ref{tab:core} "
    "specifications; bootstrap resamples trading-day clusters ($B=999$; the same-session row uses "
    "the mean of the three October-16 named repeats as the named aggregate). Level rows are paired "
    "$t$-tests at the article level ($n=341$); the same-session identity row is the revision-stage "
    "contrast of Section~\\ref{sec:results:h2} and is not part of the declared family. ``One "
    "significant, the other not'' never appears in this table by construction: all "
    "cross-instrument statements are direct difference tests.\n\\end{tablenotes}")

# ---- R7: multiple-testing summary re-interpretation ----
t = span_replace(t,
    "Three comparisons survive at any conventional threshold~---",
    "finds the contamination channels with confidence and the predictive content only marginally.",
    "Three comparisons survive at any conventional threshold~---the named-versus-anonymized level "
    "shift ($q<0.0001$), the coverage-selection test ($q=0.005$), and the reliability ICC "
    "($q<0.0001$, one-sided). The revision re-interprets the first of these: the level-shift test "
    "rejected because its contrast mixes an identity effect with a twelve-hour session gap, and "
    "the session component alone ($+5.79$, $t=7.03$) would clear any threshold; it survives as "
    "evidence of \\emph{scoring instability across sittings}, not of an identity prior "
    "(Section~\\ref{sec:results:h2}). The two channels that would constitute ``an LLM sentiment "
    "return signal''~---the baseline coefficient and its echo decomposition~---sit at $q=0.062$ "
    "and $q=0.107$ respectively. The pattern is itself informative: the audit finds the "
    "contamination and instability channels with confidence and the predictive content only "
    "marginally.")

# ---- R8: tab:bh note ----
t = t.replace(
    "Family declared in Section~\\ref{sec:data} prior to augmented inference. The three rejections "
    "are measurement-layer channels; the two return-layer channels are marginal. $q$-values from "
    "the Benjamini--Hochberg step-up procedure at $m=7$.",
    "Family declared in Section~\\ref{sec:data} prior to augmented inference. The three rejections "
    "are measurement-layer channels; the two return-layer channels are marginal. $q$-values from "
    "the Benjamini--Hochberg step-up procedure at $m=7$. The H2 level-shift row compares conditions "
    "fielded twelve hours apart; Section~\\ref{sec:results:h2} attributes most of it to "
    "between-session drift, and the same-session contrast ($p=0.11$) is a revision-stage addition "
    "outside the declared family.")

open(P, "w").write(t)
print("results.tex revised OK,", len(orig), "->", len(t), "chars")
