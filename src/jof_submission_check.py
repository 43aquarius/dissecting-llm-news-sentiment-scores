#!/usr/bin/env python3
"""jof_submission_check.py — guard for the Journal of Forecasting submission set.

Checks (all must pass):
  A. Files exist: manuscript PDF, Supporting-Information PDF, cover letter,
     declarations, README, LaTeX sources.
  B. Manuscript PDF: 27 pp (guard 25-30); SI PDF: 18 pp (guard 16-20).
  C. Manuscript page 1 (Wiley free-format title page): title, author,
     affiliation, email, abstract, JEL, keywords, data-availability,
     generative-AI, competing-interests/funding statements, MANUSCRIPT label.
  D. No 'Working Paper' label; no unresolved '??'; no 'this letter'/'FRL'
     submission framing; 'Finance Research Letters' appears exactly once
     (Kirtac & Germano 2024 bibliography citation), never as target journal.
  E. Key abstract numbers intact on page 1 (mirrors test_numbers.py values).
  F. Cover letter / declarations contain required statements incl. the
     verified no-submission-fee evidence for the target journal.

Run: python3 scripts/jof_submission_check.py
"""
import os
import re
import sys

import fitz  # PyMuPDF

# Layout-portable: works both from canonical scripts/ and from in-repo src/
# (both hold the script two levels below a directory containing submission_jof/).
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.join(BASE, "submission_jof")
if not os.path.isdir(ROOT):
    ROOT = "/home/z/my-project/submission_jof"  # fallback for alternate layouts
MANU = os.path.join(ROOT, "Dissecting_LLM_Sentiment_JoF_Manuscript.pdf")
SI = os.path.join(ROOT, "Dissecting_LLM_Sentiment_JoF_Supporting_Information.pdf")
COVER = os.path.join(ROOT, "cover_letter_JoF.md")
DECL = os.path.join(ROOT, "declarations_JoF.md")
README = os.path.join(ROOT, "README_JoF_Submission.md")

ok = True


def check(label: str, cond: bool) -> None:
    global ok
    mark = "PASS" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"[{mark}] {label}")


def main() -> None:
    # ---- A. files ----
    for p in (MANU, SI, COVER, DECL, README):
        check(f"exists: {os.path.basename(p)}", os.path.isfile(p))
    for src in ("main.tex", "online_appendix.tex", "sections/titleblock.tex"):
        check(f"source exists: {src}", os.path.isfile(os.path.join(ROOT, src)))

    # source-level label guard
    tb = open(os.path.join(ROOT, "sections/titleblock.tex"), encoding="utf-8").read()
    check("titleblock source: 'Manuscript' label", "\\scshape Manuscript" in tb)
    check("titleblock source: no 'Working Paper'", "Working Paper" not in tb)

    m = fitz.open(MANU)
    s = fitz.open(SI)
    mp1 = m[0].get_text()
    mfull = "".join(pg.get_text() for pg in m)
    sfull = "".join(pg.get_text() for pg in s)

    # ---- B. page counts ----
    check(f"manuscript pages = {len(m)} (guard 25-30)", 25 <= len(m) <= 30)
    check(f"SI pages = {len(s)} (guard 16-20)", 16 <= len(s) <= 20)

    # ---- C. title page elements ----
    check("p1: MANUSCRIPT label", "MANUSCRIPT" in mp1 or "Manuscript" in mp1)
    check("p1: title", "Dissecting LLM News Sentiment Scores" in mp1)
    check("p1: subtitle (measurement audit)", "A Measurement Audit" in mp1)
    check("p1: author Chang Tan", "Chang Tan" in mp1)
    check("p1: affiliation DUT", "Dalian University of Technology" in mp1)
    check("p1: email", "aquars43@foxmail.com" in mp1)
    check("p1: Abstract present", "Abstract." in mp1)
    check("p1: JEL classification", "JEL classification" in mp1)
    check("p1: Keywords", "Keywords:" in mp1)
    mp1n = re.sub(r"\s+", " ", mp1)  # collapse line-wraps for phrase checks
    check("p1: Data and code availability", "Data and code availability" in mp1n)
    check("p1: Generative-AI use", bool(re.search(r"Generative-\s*AI\s+use", mp1)))
    check("p1: Competing interests and funding", "Competing interests and funding" in mp1n)

    # ---- D. hygiene ----
    check("manuscript: no 'Working Paper'", "Working Paper" not in mfull)
    check("SI: no 'Working Paper'", "Working Paper" not in sfull)
    check(f"manuscript unresolved ?? = {mfull.count('??')} (need 0)", mfull.count("??") == 0)
    check(f"SI unresolved ?? = {sfull.count('??')} (need 0)", sfull.count("??") == 0)
    frl_m = mfull.count("Finance Research Letters")
    frl_s = sfull.count("Finance Research Letters")
    check(f"manuscript FRL mentions = {frl_m} (need exactly 1, bibliography only)", frl_m == 1)
    check(f"SI FRL mentions = {frl_s} (need exactly 1, bibliography only)", frl_s == 1)
    check("no 'this letter' framing (manuscript)", "this letter" not in mfull.lower())
    check("no 'FRL' token (manuscript)", not re.search(r"\bFRL\b", mfull))
    check("no 'companion letter' (manuscript)", "companion letter" not in mfull.lower())

    # ---- E. key abstract numbers on page 1 (mirror test_numbers.py) ----
    for num, label in [
        ("2.10", "baseline t=2.10"),
        ("0.062", "BH q=0.062"),
        ("2.6", "pooled de-identification +2.6"),
        ("1.1", "CI lower 1.1"),
        ("4.1", "CI upper 4.1"),
        ("3.6", "batch composition 3.6"),
        ("0.92", "ICC 0.92"),
        ("30%", "30% exact replication"),
        ("0.10", "echo p=0.10"),
        ("2.76", "coverage selection t=2.76"),
    ]:
        check(f"p1 number intact: {label}", num in mp1)

    # ---- SI structure ----
    sp1 = s[0].get_text()
    check("SI: 'Online Appendix' label", "Online Appendix" in sp1 or "ONLINE APPENDIX" in sp1.upper())
    check("SI: author on SI title page", "Chang Tan" in sp1)
    check("SI: Appendices A-K present", "Appendices A" in sp1)

    # ---- F. documents ----
    cover = open(COVER, encoding="utf-8").read()
    decl = open(DECL, encoding="utf-8").read()
    readme = open(README, encoding="utf-8").read()
    check("cover letter: names Journal of Forecasting", "Journal of Forecasting" in cover)
    check("cover letter: originality / not under consideration", "not under consideration elsewhere" in cover)
    check("cover letter: competing-interest statement", "no competing interests" in cover)
    check("cover letter: data availability mention", "replication package" in cover)
    decl_items = ["Funding", "Competing interests", "Data availability",
                  "Generative AI use", "Author contributions", "Ethics", "ORCID"]
    for item in decl_items:
        check(f"declarations: {item} section", item.lower() in decl.lower())
    check("declarations: verified no-fee quote", "does not charge submission fees" in decl)
    check("README: portal URL", "authors.wiley.com/journal/for" in readme)
    check("README: slot mapping (Manuscript)", "Dissecting_LLM_Sentiment_JoF_Manuscript.pdf" in readme)
    check("README: slot mapping (Supporting Information)", "Supporting_Information.pdf" in readme)

    # ---- evidence block ----
    print("\nTarget journal evidence:")
    print("  Journal of Forecasting (Wiley), submission portal https://authors.wiley.com/journal/for")
    print("  Fee status verified 2026-10-29 from official For-Authors page:")
    print('  "This journal does not charge submission fees." (free-format submission;')
    print("   subscription route = no publication charge; OA optional)")

    print()
    if ok:
        print("jof_submission_check: ALL CHECKS PASS")
    else:
        print("jof_submission_check: FAILURES PRESENT")
        sys.exit(1)


if __name__ == "__main__":
    main()
