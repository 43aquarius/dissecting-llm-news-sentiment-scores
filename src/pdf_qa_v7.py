#!/usr/bin/env python3
"""PDF QA v6.5: page sizes, fonts, margins, key strings for the SPLIT deliverable set.

Main paper (cover + main text) and Online Appendix are now separate PDFs;
this net checks both, plus structural page-count guards.
"""
import fitz

MAIN = "/home/z/my-project/download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf"
OA = "/home/z/my-project/download/Dissecting_LLM_News_Sentiment_Scores_Online_Appendix.pdf"
LETTER = "/home/z/my-project/download/submission_frl/frl_letter.pdf"

def struct(doc, name, max_pages):
    issues = []
    for i, page in enumerate(doc):
        r = page.rect
        if abs(r.width - 595.3) > 1.0 or abs(r.height - 841.9) > 1.0:
            issues.append(f"page {i+1} size {r.width:.1f}x{r.height:.1f}")
    unembedded = set()
    for i in range(len(doc)):
        for f in doc[i].get_fonts():
            if f[3] not in ("", None) and f[1] == "":
                unembedded.add(f[3])
    print(f"{name}: {len(doc)} pages (guard <= {max_pages}), size issues: {len(issues)}, unembedded fonts: {len(unembedded)}")
    if len(doc) > max_pages:
        print(f"  FAIL {name} exceeds page guard")
    if issues:
        print("   ", issues[:5])
    if unembedded:
        print("   ", list(unembedded)[:5])
    return len(issues) == 0 and len(unembedded) == 0 and len(doc) <= max_pages

def texts(path):
    doc = fitz.open(path)
    full = "\n".join(p.get_text() for p in doc)
    import re as _re
    keep = _re.sub(r'\s+', ' ', _re.sub(r'-\n', '-', full))
    drop = _re.sub(r'\s+', ' ', _re.sub(r'-\n', '', full))
    return full, keep, drop

def present(x, srcs):
    return any(x in s for s in srcs)

ok = True
main_doc = fitz.open(MAIN)
oa_doc = fitz.open(OA)
letter_doc = fitz.open(LETTER)
ok &= struct(main_doc, "MAIN", 30)
ok &= struct(oa_doc, "OA", 22)
# letter: US Letter or A4 both acceptable for a journal submission letter
_lw, _lh = letter_doc[0].rect.width, letter_doc[0].rect.height
_letter_ok = abs(_lw - 612) < 1 and abs(_lh - 792) < 1 or abs(_lw - 595.3) < 1 and abs(_lh - 841.9) < 1
print(f"LETTER: {len(letter_doc)} pages, page size {_lw:.0f}x{_lh:.0f} ({'ok' if _letter_ok else 'FAIL'})")
ok &= _letter_ok and len(letter_doc) <= 14

# margins (text blocks within 2.5cm = 68pt, small tolerance)
def margins(doc, name):
    bad = []
    for i, page in enumerate(doc):
        if i == 0 and name == "MAIN":
            continue  # cover footer is a design element (v6.4 convention)
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            if (x1 > 595.3 - 64 or x0 < 64) and text.strip() and len(text.strip()) > 3:
                bad.append((i + 1, round(x0, 1), round(x1, 1), text.strip()[:36]))
    print(f"{name} blocks outside margins: {len(bad)}")
    for o in bad[:5]:
        print("   ", o)
    return len(bad) == 0

ok &= margins(main_doc, "MAIN")
ok &= margins(oa_doc, "OA")

mfull, mkeep, mdrop = texts(MAIN)
ofull, okeep, odrop = texts(OA)
mnospace = "".join(mfull.split())
onospace = "".join(ofull.split())

main_must = [
    # core statistics
    "0.0144", "0.0149", "2.76", "0.062", "0.140", "0.100", "29.9%",
    "0.0283", "−1.29", "0.36", "−2.82", "3.61", "0.0475", "82.7",
    "draw-dependent", "276 unique firm", "9,999",
    "one-fourteenth of the price-language", "one-fifth of the baseline",
    "2,628", "39 of the 240", "fourteen re-scorings", "BatchPrompt", "104335",
    "22 to 50 firm-days", "batch_downstream.py",
    "temperature", "glm-4-plus", "De-Identification", "de-identification effect",
    "−2.05", "0.34", "83.3", "0.0179", "4.8", "sixteen archived",
    "telescoping identity", "model_fingerprint.log",
    "Christensen and Hansen", "Bisharat and Hean", "AEA Papers and Proceedings",
    "not yet evidence of equivalence", "21–42", "56%", "formally equivalent",
    "0.0658", "0.0136", "two-one-sided-tests", "descriptives.py",
    # v6.5: pooled estimate, wide-null batch-size, point-estimate reading
    "−2.57", "2.6 points pooled across three sessions", "leaves the presence channel open",
    "point-estimate reading", "Online Appendix", "−4.92", "5.5–5.7",
    "DerSimonian", "−4.56", "fourteen individual passes",
]
oa_must = [
    "Minimal Viable Audit Protocol", "coverage_table.py",
    "equivalence margin threshold", "equivalence_testing.py",
    "Level-layer equivalence", "Cross-session pooled estimate",
    "meta_deident_pooling.py", "results_meta_deident.json",
    "near-identical", "The downstream consequences of batch composition",
    "P2_preregistration_session5", "P3_preregistration_session6",
    "level_tost_and_margins.py", "swap_leakage_audit.py",
    "Batch-Size Dose-Response", "Uninformative", "2.9%",
    "a wide null rather than a zero point", "figures_v7.py",
    "The naive two-session benchmark, archived in full",
    "13.90", "interleaved session establishes the de-identification effect",
]

mmiss = [m for m in main_must if not present(m, (mfull, mkeep, mdrop, mnospace))]
omiss = [m for m in oa_must if not present(m, (ofull, okeep, odrop, onospace))]
print(f"MAIN key-string spot check: {len(main_must)-len(mmiss)}/{len(main_must)} present")
if mmiss:
    print("  missing:", mmiss)
print(f"OA key-string spot check: {len(oa_must)-len(omiss)}/{len(oa_must)} present")
if omiss:
    print("  missing:", omiss)

# stale overclaims must be gone from BOTH
stale = ["mere batch-mate presence does not move levels",
         "the batch-size-1 zero point is level-neutral",
         "Batch-Size Zero Point",
         "thirteen individual passes",
         "(a fictional-name control recovers about half)"]
both = (mfull + " " + ofull)
found = [s for s in stale if present(s, (both,))]
print(f"stale-phrase scan: {len(found)} found (must be 0)")
if found:
    print("  STALE:", found)

# cross-resolution: no ?? anywhere
qq_m = [i+1 for i in range(len(main_doc)) if '??' in main_doc[i].get_text()]
qq_o = [i+1 for i in range(len(oa_doc)) if '??' in oa_doc[i].get_text()]
print(f"unresolved ?? : MAIN {qq_m} OA {qq_o}")

all_ok = ok and not mmiss and not omiss and not found and not qq_m and not qq_o
print("\nPDF QA v6.5:", "PASS" if all_ok else "FAIL")
