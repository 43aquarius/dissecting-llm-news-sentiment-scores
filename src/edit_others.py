#!/usr/bin/env python3
"""Apply revision edits to robustness.tex, discussion.tex, conclusion.tex, data.tex, appendix.tex."""

def apply(path, edits):
    t = open(path).read()
    for i, (old, new, label) in enumerate(edits):
        if new in t and old not in t:
            print(f"  [{label}] already applied, skip")
            continue
        assert old in t, f"  [{label}] OLD NOT FOUND in {path}"
        t = t.replace(old, new, 1)
        print(f"  [{label}] OK")
    open(path, "w").write(t)

# ================= robustness.tex =================
ROB = "/home/z/my-project/paper/sections/robustness.tex"
rob_edits = [
    # new subsection after specification robustness
    ("The consistent picture across (i)--(v) is a real but fragile association~---robust to measurement choices, weakened by event-day down-weighting, and significant at conventional levels only under the original sample construction.",
     "The consistent picture across (i)--(v) is a real but fragile association~---robust to measurement choices, weakened by event-day down-weighting, and significant at conventional levels only under the original sample construction.\n\n"
     "\\subsection{Session robustness of the predictive coefficient}\n\n"
     "The baseline coefficient rests on October-15 scores; the three October-16 named repeats re-score the identical headlines in a different sitting. The next-day coefficient is $0.0149$ ($t=2.10$) on the original round and $0.0146$ ($t=2.12$), $0.0145$ ($t=1.76$), and $0.0128$ ($t=1.68$) on the three repeats individually, $0.0147$ ($t=1.87$) on their firm-day mean: the point estimate is stable across sessions to well within its own standard error, and every repeat falls inside the range the specification checks above already span. The same-day loading is likewise large under every repeat ($t$ between $2.96$ and $3.80$). Session drift is therefore a \\emph{level} phenomenon~---it moves the mean score by about six points (Section~\\ref{sec:results:h2})~---not a \\emph{slope} phenomenon: predictive loadings survive re-scoring, which is the robustness fact every other result in this paper leans on. The same-session instrument difference is itself stable: the anonymized-versus-named predictive difference re-estimated entirely inside the October-16 sitting is $0.0002$ ($p=0.905$), tracking its cross-session twin ($p=0.887$).",
     "rob-session-subsection"),
    # threats: single scorer paragraph
    ("\\emph{Single scorer}: all conditions use one model endpoint; cross-model stability (the model-variability problem of \\citealp{herrera2025}) is not tested here, and the served model may have been updated between the original round and the audit rounds (days apart); the repeat-call ICC therefore bounds within-endpoint, near-term stability only.",
     "\\emph{Single scorer}: all conditions use one model endpoint; cross-model stability (the model-variability problem of \\citealp{herrera2025}) is not tested here. The audit rounds ran twelve hours after the original round, and the identical named protocol drifted $+5.8$ points in level between sittings (Section~\\ref{sec:results:h2}); we cannot attribute that drift to a served-model update versus batch-composition differences, and the repeat-call ICC therefore bounds near-term stability only.",
     "rob-threat-scorer"),
    # threats: external validity anonymity claim
    ("and the anonymization level effect may differ where firm priors are weaker.",
     "and any identity level effect~---which this corpus bounds to about one point~---may differ where firm priors are stronger.",
     "rob-threat-extval"),
]

# ================= discussion.tex =================
DIS = "/home/z/my-project/paper/sections/discussion.tex"
dis_edits = [
    ("Assembling the five audit results: the association between LLM news sentiment and next-day returns on this sample is (i)~marginal under family-wise standards and weakens once the same-day return is controlled; (ii)~indistinguishable, as a predictive coefficient, from the anonymized condition and from the dictionary;",
     "Assembling the five audit results: the association between LLM news sentiment and next-day returns on this sample is (i)~marginal under family-wise standards and weakens once the same-day return is controlled; (ii)~indistinguishable, as a predictive coefficient, from the anonymized condition and from the dictionary, with its apparent identity level shift re-attributed by the revision to between-session drift;",
     "dis-synthesis"),
    ("Under the decomposition~\\eqref{eq:score}, the reading is: $\\iota\\neq 0$ (identity prior, level only), $\\Var(\\varepsilon)$ substantial,",
     "Under the decomposition~\\eqref{eq:score}, the reading is: $\\iota$ small and statistically unmeasured at this precision (the cross-session level gap is session drift $\\eta$, not prior $\\iota G_i$), $\\Var(\\varepsilon)$ substantial,",
     "dis-reading"),
    ("The experiment is cheap (one additional scoring pass), it separates priors from information (H2), and in post-cutoff windows it is the direct test of whether identity effects survive the removal of memorization as an explanation~---complementing the in-sample results of \\citet{glasserman2023}.",
     "The experiment is cheap (one additional scoring pass), it separates priors from information (H2), and in post-cutoff windows it is the direct test of whether identity effects survive the removal of memorization as an explanation~---complementing the in-sample results of \\citet{glasserman2023}. One protocol detail is now load-bearing: field the contrast \\emph{in the same sitting} as its named twin. The audit's own initial estimate of this shift was confounded by a twelve-hour gap between sittings (Section~\\ref{sec:results:h2})~---a $+5.8$-point drift in the identical protocol~---a mistake that same-session interleaving structurally prevents.",
     "dis-implication1"),
    ("A cross-model replication showing the same identity level shift would firm up the prior interpretation of H2.",
     "A cross-model, same-session replication with interleaved conditions that found an identity level shift would establish the prior channel that this corpus bounds to about one point.",
     "dis-wouldchange"),
    ("\\emph{Instrument.} One model, one endpoint, default decoding, no version pinning beyond what the provider exposes; the four scoring conditions were executed within hours of each other but we cannot certify endpoint stability over longer horizons, and cross-model generalization is untested. The anonymization is conservative (names and tickers only): product names, tickers of other firms mentioned in a headline, and stylistic cues survive, so the anonymized condition is a lower bound on de-identification, and some identity information plausibly remains.",
     "\\emph{Instrument.} One model, one endpoint, default decoding, no version pinning beyond what the provider exposes; the four scoring conditions were fielded in two sittings twelve hours apart, between which the identical named protocol drifted $+5.8$ points in level (Section~\\ref{sec:results:h2})~---we cannot attribute the drift to endpoint change versus batch composition, and cannot certify stability over longer horizons; cross-model generalization is untested. The anonymization is conservative (names and tickers only): product names and stylistic cues survive, and 6 of 341 anonymized headlines (1.8\\%) still name another sample firm~---typically an analyst house or co-mentioned mega-cap (Appendix~\\ref{app:anon})~---so the anonymized condition remains a lower bound on de-identification.",
     "dis-limitations-instrument"),
]

# ================= conclusion.tex =================
CON = "/home/z/my-project/paper/sections/conclusion.tex"
con_edits = [
    ("Firm identity systematically inflates the level of scores by 4.75 points without changing their predictive content.",
     "A 4.75-point named-versus-anonymized gap that initially looked like a firm prior decomposes, under the same-session benchmark added in revision, into $+5.79$ points of between-session drift and a $-1.04$-point residual indistinguishable from zero~---the audit caught its own initial conclusion, which is the strongest argument we know for the protocol it recommends.",
     "con-identity"),
    ("The instrument is reliable but stochastic (ICC $0.919$; 44\\% exact replication).",
     "The instrument is reliable but stochastic (ICC $0.919$ pooled across two sessions; $0.949$ within one; 44\\% exact replication).",
     "con-icc"),
    ("The protocol that fell out of this exercise is deliberately minimal: anonymize once and benchmark the difference; repeat-call once and report the noise floor;",
     "The protocol that fell out of this exercise is deliberately minimal: anonymize once and benchmark the difference in the same scoring session; repeat-call once and report the noise floor;",
     "con-protocol"),
    ("the post-cutoff window is the clean laboratory for identity effects, and the level-shift-without-predictive-shift signature documented here is a precise target for cross-model and cross-market replication.",
     "the post-cutoff window is the clean laboratory for identity effects, and the session-drift signature documented here~---a $+5.8$-point level move of the identical protocol across a twelve-hour gap~---is a precise target for cross-model and cross-market replication.",
     "con-signature"),
]

# ================= data.tex =================
DAT = "/home/z/my-project/paper/sections/data.tex"
dat_edits = [
    ("All raw responses, batch logs with timestamps, and the alias table are archived in the replication package. Because the anonymization and repeat rounds postdate the original round only by hours and use the same model endpoint, any drift in the served model over time is a limitation we acknowledge in Section~\\ref{sec:limitations}.",
     "All raw responses, batch logs with timestamps, and the alias table are archived in the replication package. The anonymization and repeat rounds ran in a single 2026-10-16 sitting (04:24--04:33 UTC), twelve hours after the original round (2026-10-15, 16:01--16:24 UTC), under a protocol that is verbatim-identical for the named conditions; the between-session drift this gap admits is measured in Section~\\ref{sec:results:h2} and Appendix~\\ref{app:session}.",
     "dat-timestamps"),
]

# ================= appendix.tex =================
APP = "/home/z/my-project/paper/sections/appendix.tex"
app_edits = [
    ("The procedure is conservative: product names, third-party firms mentioned inside a headline, and stylistic cues are left intact, so the anonymized condition is a lower bound on de-identification.",
     "The procedure is conservative: product names, third-party firms mentioned inside a headline, and stylistic cues are left intact, so the anonymized condition is a lower bound on de-identification. Quantifying the residual firm-identity component: 6 of 341 anonymized headlines (1.8\\%) still name at least one other sample firm~---under both a case-insensitive and a case-sensitive matching convention on the same alias table~---with analyst actions (``BofA,'' ``Morgan Stanley'') and co-mentioned mega-caps the typical cases. The dominant de-identification gap is therefore product language (e.g., device or franchise names) rather than residual firm names.",
     "app-anon-quantify"),
]

apply(ROB, rob_edits)
apply(DIS, dis_edits)
apply(CON, con_edits)
apply(DAT, dat_edits)
apply(APP, app_edits)
print("all files done")
