#!/usr/bin/env python3
"""PDF QA for the v4 deliverable: page sizes, fonts, text-in-margin, key numbers."""
import fitz

PDF = "/home/z/my-project/download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf"
doc = fitz.open(PDF)
issues = []

# 1. page sizes
for i, page in enumerate(doc):
    r = page.rect
    if abs(r.width - 595.3) > 1.0 or abs(r.height - 841.9) > 1.0:
        issues.append(f"page {i+1} size {r.width:.1f}x{r.height:.1f}")

# 2. fonts embedded
unembedded = set()
for i in range(len(doc)):
    for f in doc[i].get_fonts():
        if f[3] not in ("", None) and f[1] == "":
            unembedded.add(f[3])

# 3. text within margins (2.5cm = 70.9pt; allow images to extend)
RIGHT = 595.3 - 68
LEFT = 68
overflow = []
for i, page in enumerate(doc):
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
        if x1 > RIGHT + 4 or x0 < LEFT - 4:
            if text.strip() and len(text.strip()) > 3:
                overflow.append((i + 1, round(x0, 1), round(x1, 1), text.strip()[:40]))

print(f"pages: {len(doc)}")
print(f"page-size issues: {len(issues)}", issues[:5])
print(f"unembedded fonts: {len(unembedded)}")
print(f"text blocks outside margins: {len(overflow)}")
for o in overflow[:8]:
    print("  ", o)

# 4. spot-check key numbers
full = "\n".join(p.get_text() for p in doc)
must_have = ["0.0144", "0.0149", "2.76", "0.014", "0.140", "0.100", "29.9%",
             "Remark 1", "0.0283", "-1.29", "2.9%", "1.825", "0.36",
             "276 unique firm", "9,999", "descriptives.py", "coverage_table.py"]
missing = [m for m in must_have if m not in full]
print(f"key-number spot check: {len(must_have)-len(missing)}/{len(must_have)} present")
if missing:
    print("  missing:", missing)
