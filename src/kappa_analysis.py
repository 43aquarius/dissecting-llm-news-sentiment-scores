#!/usr/bin/env python3
"""Inter-rater reliability analysis for the echo-classifier annotation package.

Reads the annotation sheet (annotation_package/annotation_sheet.csv) once BOTH
human raters have filled rater1_label / rater2_label, and computes:
  - Cohen's kappa between the two human raters
  - each human rater's raw and kappa agreement with the LLM-assisted audit labels
  - the strict-P re-definition of the echo split under human labels (counts only)
  - a confusion matrix and the list of disagreements

If the sheet is not yet filled, the script reports what is missing and exits
without fabricating anything.

Usage: python3 kappa_analysis.py [path/to/annotation_sheet.csv]
Writes: annotation_package/kappa_report.json
"""
import json
import sys
import csv
from collections import Counter

SHEET = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/z/my-project/replication_package_v2/annotation_package/annotation_sheet.csv"
OUT = SHEET.replace("annotation_sheet.csv", "kappa_report.json")
CATS = ["P", "E", "D", "N"]


def cohen_kappa(a, b):
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    cnt_a, cnt_b = Counter(a), Counter(b)
    pe = sum(cnt_a[c] / n * cnt_b[c] / n for c in CATS)
    if pe == 1:
        return float("nan")
    return (po - pe) / (1 - pe)


rows = list(csv.DictReader(open(SHEET)))
r1 = [r["rater1_label"].strip().upper() for r in rows]
r2 = [r["rater2_label"].strip().upper() for r in rows]
llm = [r["llm_audit_label"].strip().upper() for r in rows]
titles = [r["title"] for r in rows]

missing = {"rater1": sum(1 for x in r1 if x not in CATS),
           "rater2": sum(1 for x in r2 if x not in CATS)}
if missing["rater1"] or missing["rater2"]:
    print(f"ANNOTATION INCOMPLETE: rater1 missing {missing['rater1']}/{len(rows)}, "
          f"rater2 missing {missing['rater2']}/{len(rows)}. "
          "No statistics computed (nothing is imputed or fabricated).")
    sys.exit(0)

k_rr = cohen_kappa(r1, r2)
k_1l = cohen_kappa(r1, llm)
k_2l = cohen_kappa(r2, llm)
agree_rr = sum(1 for x, y in zip(r1, r2) if x == y)
strict_p_human = [i for i in range(len(rows)) if r1[i] == "P" and r2[i] == "P"]

confusion = {c: {d: sum(1 for x, y in zip(r1, r2) if x == c and y == d) for d in CATS}
             for c in CATS}
disagree_rr = [{"iid": i, "title": titles[i], "rater1": r1[i], "rater2": r2[i]}
               for i in range(len(rows)) if r1[i] != r2[i]]
disagree_llm = [{"iid": i, "title": titles[i], "r1": r1[i], "r2": r2[i], "llm": llm[i]}
                for i in range(len(rows)) if r1[i] == r2[i] and r1[i] != llm[i]]

report = {
    "n": len(rows),
    "cohen_kappa_rater1_rater2": k_rr,
    "raw_agreement_rater1_rater2": agree_rr / len(rows),
    "cohen_kappa_rater1_llm": k_1l,
    "cohen_kappa_rater2_llm": k_2l,
    "confusion_r1_r2": confusion,
    "strict_P_both_raters_count": len(strict_p_human),
    "disagreements_rater1_rater2": disagree_rr,
    "consensus_disagrees_with_llm": disagree_llm,
}
json.dump(report, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in report.items() if k not in
                  ("disagreements_rater1_rater2", "consensus_disagrees_with_llm")}, indent=1))
print(f"wrote {OUT}")
