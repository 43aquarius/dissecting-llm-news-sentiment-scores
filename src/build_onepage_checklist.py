#!/usr/bin/env python3
"""L3-2: build the standalone one-page Minimal Audit Protocol checklist.
Extracts the app:checklist section verbatim from appendix.tex (so the
checklist and the paper can never drift), wraps it in a one-page A4 document,
compiles with Tectonic -> download/Audit_Protocol_Checklist_OnePage.pdf."""
import re
import subprocess

APP = "/home/z/my-project/paper/sections/appendix.tex"
OUT_DIR = "/home/z/my-project/paper"
TEX = f"{OUT_DIR}/checklist_onepage.tex"
PDF_OUT = "/home/z/my-project/download/Audit_Protocol_Checklist_OnePage.pdf"

app = open(APP).read()
start = app.index("\\section{A Minimal Viable Audit Protocol}")
end = app.index("\n\\section", start + 10) if "\n\\section" in app[start + 10:] else len(app)
sec = app[start:end]

# intro sentence
m_intro = re.search(r"\\label\{app:checklist\}\n\n(.*?)\n\n\\begin\{enumerate\}", sec, re.S)
intro = m_intro.group(1).strip()
# enumerate items (verbatim, incl. nested commands)
m_items = re.search(r"\\begin\{enumerate\}(.*?)\\end\{enumerate\}", sec, re.S)
items = m_items.group(1).strip()
# closing paragraph
m_close = re.search(r"\\end\{enumerate\}\n\n(.*?)$", sec + "\n", re.S)
close = m_close.group(1).strip()
# strip \section line from close if captured
close = re.sub(r"\\section\{.*$", "", close, flags=re.S).strip()

tex = r"""\documentclass[10pt,a4paper]{article}
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{newtxtext,newtxmath}
\usepackage{geometry}
\geometry{a4paper, top=1.8cm, bottom=1.6cm, left=1.9cm, right=1.9cm}
\usepackage{enumitem}
\usepackage{xcolor}
\usepackage[colorlinks=true, linkcolor=blue, urlcolor=blue]{hyperref}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\pagestyle{empty}
\begin{document}
\begin{center}
{\LARGE\bfseries Minimal Audit Protocol}\\[3pt]
{\large\itshape For LLM-sentiment return-predictability studies (one page, checklist form)}\\[6pt]
{\small Companion to \emph{Dissecting LLM News Sentiment Scores: De-Identification, Batch Composition,
Scoring Noise, and Price Echoes in Return Predictability} (working paper, Appendix).}\\[2pt]
{\small Replication package: \url{https://github.com/43aquaris/dissecting-llm-news-sentiment-scores}}
\end{center}
\vspace{2pt}
\rule{\textwidth}{0.6pt}
""" + intro + r"""

\vspace{2pt}
\begin{enumerate}[leftmargin=1.4em, itemsep=4pt, topsep=2pt]
""" + items + r"""
\end{enumerate}
\vspace{2pt}
\rule{\textwidth}{0.4pt}
\vspace{1pt}
""" + close + r"""

\vspace{4pt}
{\footnotesize\emph{Checklist form of Appendix ``A Minimal Viable Audit Protocol''; the paper's appendix is
the authoritative text and the two are generated from the same source. Free to reuse with citation.}}
\end{document}
"""
# the appendix items reference Sections/Tables of the parent paper; keep them but soften refs
# the appendix items cross-reference Sections/Tables of the parent paper; in the
# standalone checklist every cross-reference becomes a generic, balanced pointer
import re as _re
tex = _re.sub(r"([A-Za-z]+)~\\\\ref\{[^}]+\}", r"\1 of the parent paper", tex)
open(TEX, "w").write(tex)

r = subprocess.run(["tectonic", "-o", OUT_DIR, TEX], capture_output=True, text=True, timeout=300)
print(r.stdout[-400:] if r.stdout else "", r.stderr[-600:] if r.stderr else "")
import shutil, os
src = f"{OUT_DIR}/checklist_onepage.pdf"
shutil.copy(src, PDF_OUT)
import pypdf
print("pages:", len(pypdf.PdfReader(PDF_OUT).pages))
print("written:", PDF_OUT)
