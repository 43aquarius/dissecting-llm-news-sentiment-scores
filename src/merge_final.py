#!/usr/bin/env python3
"""Merge cover.pdf + main.pdf -> final deliverable with A4 normalization and metadata."""
from pypdf import PdfReader, PdfWriter

COVER = "/home/z/my-project/paper/cover.pdf"
BODY = "/home/z/my-project/paper/main.pdf"
OUT = "/home/z/my-project/download/Dissecting_LLM_News_Sentiment_Signals_Audit_Working_Paper.pdf"

w = PdfWriter()
for src in (COVER, BODY):
    r = PdfReader(src)
    for pg in r.pages:
        # normalize to A4 (595.3 x 841.9 pt)
        pg.scale_to(width=595.3, height=841.9)
        w.add_page(pg)

w.add_metadata({
    "/Title": "Dissecting LLM News Sentiment Scores: De-Identification, Batch Composition, Scoring Noise, and Price Echoes in Return Predictability",
    "/Author": "Chang Tan",
    "/Subject": "Measurement audit of LLM news sentiment scoring for stock return prediction",
    "/Keywords": "large language models; sentiment analysis; return predictability; measurement validity; batch composition; look-ahead bias; replication",
    "/Creator": "Tectonic + pypdf pipeline",
})
with open(OUT, "wb") as f:
    w.write(f)
r = PdfReader(OUT)
print(f"written {OUT}: {len(r.pages)} pages")
