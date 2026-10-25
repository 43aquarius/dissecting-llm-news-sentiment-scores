#!/usr/bin/env python3
"""Layer-2 leakage audit (user directive, 2026-10-25):

The session-5 swap control replaced each headline's FOCAL identifiers (company
name + ticker) with another firm's identifiers. Company-specific cues that the
replacement does not touch -- product names, platform names, executive names,
media nicknames -- can remain, making part of the swapped text non-coherent
(or still identity-informative). This script:

1. rebuilds the 341 swapped texts exactly as session 5 did (same alias table,
   same seeded swap map);
2. derives a transparent, data-driven cue lexicon per firm from the named
   corpus itself: a token is a firm-specific cue if it appears in >= 3 of that
   firm's in-window titles (sensitivity: >= 2) and in <= 7 other firms'
   titles, is not the firm's own name/ticker/alias, and is not a pure number;
3. flags swapped headlines that still contain >= 1 cue of the ORIGINAL firm;
4. re-runs the key level contrasts (N5-S5, S5-A5, N5-A5) on the unflagged
   subsample under headline-level and 14-cluster-clustered inference.

This is a lexical heuristic, disclosed as such (not human annotation).
Outputs: data/results_swap_leakage.json, data/s6_cue_lexicon.json.
"""
import json
import math
import random
import re
import statistics as st

DATA = "/home/z/my-project/data"
SEED = 20261025
B = 9999
Z90 = 1.6448536269514722

ALIASES = {
  "AAPL": ["Apple"], "MSFT": ["Microsoft"], "NVDA": ["Nvidia", "NVIDIA"], "GOOGL": ["Alphabet", "Google"],
  "AMZN": ["Amazon"], "META": ["Meta Platforms", "Meta", "Facebook"], "TSLA": ["Tesla"], "AVGO": ["Broadcom"],
  "AMD": ["Advanced Micro Devices", "AMD"], "NFLX": ["Netflix"], "INTC": ["Intel"], "ORCL": ["Oracle"],
  "CRM": ["Salesforce"], "ADBE": ["Adobe"], "QCOM": ["Qualcomm"], "IBM": ["IBM"],
  "JPM": ["JPMorgan Chase", "JPMorgan", "J.P. Morgan"], "BAC": ["Bank of America", "BofA"],
  "GS": ["Goldman Sachs"], "MS": ["Morgan Stanley"], "WFC": ["Wells Fargo"], "V": ["Visa"],
  "MA": ["Mastercard"], "XOM": ["Exxon Mobil", "Exxon"], "CVX": ["Chevron"], "PG": ["Procter & Gamble", "P&G"],
  "KO": ["Coca-Cola", "Coca Cola", "Coke"], "WMT": ["Walmart", "Wal-Mart"], "COST": ["Costco"],
  "JNJ": ["Johnson & Johnson", "Johnson and Johnson"], "LLY": ["Eli Lilly", "Lilly"], "DIS": ["Disney"],
  "BA": ["Boeing"], "CAT": ["Caterpillar"], "GE": ["GE Aerospace", "General Electric"], "PFE": ["Pfizer"],
}
DISPLAY = {
  "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "GOOGL": "Alphabet", "AMZN": "Amazon",
  "META": "Meta Platforms", "TSLA": "Tesla", "AVGO": "Broadcom", "AMD": "Advanced Micro Devices",
  "NFLX": "Netflix", "INTC": "Intel", "ORCL": "Oracle", "CRM": "Salesforce", "ADBE": "Adobe",
  "QCOM": "Qualcomm", "IBM": "IBM", "JPM": "JPMorgan Chase", "BAC": "Bank of America", "GS": "Goldman Sachs",
  "MS": "Morgan Stanley", "WFC": "Wells Fargo", "V": "Visa", "MA": "Mastercard", "XOM": "Exxon Mobil",
  "CVX": "Chevron", "PG": "Procter & Gamble", "KO": "Coca-Cola", "WMT": "Walmart", "COST": "Costco",
  "JNJ": "Johnson & Johnson", "LLY": "Eli Lilly", "DIS": "Disney", "BA": "Boeing", "CAT": "Caterpillar",
  "GE": "GE Aerospace", "PFE": "Pfizer",
}

def esc(s):
    return re.sub(r"[.*+?^${}()|[\]\\&]", r"\\&", s)

def replace_focal(title, ticker, replacement_name, replacement_ticker):
    t = title
    for token in sorted(ALIASES[ticker], key=len, reverse=True):
        t = re.sub(rf"\b{esc(token)}\b", replacement_name, t, flags=re.I)
    t = re.sub(rf"\b{ticker}\b", replacement_ticker, t)
    t = re.sub(rf"\b{replacement_name}( {replacement_name})+\b", replacement_name, t)
    return t

def tokenize(title):
    return [w for w in re.findall(r"[A-Za-z][A-Za-z&'\-]{2,}", title)]

def load(name):
    with open(f"{DATA}/{name}") as f:
        return json.load(f)

scored = load("news_scored.json")
inwin = [a for a in scored if a.get("date_iso") and "2026-07-01" <= a["date_iso"] <= "2026-10-14"]
assert len(inwin) == 341
swap = load("s5_swap_map.json")

# 1. rebuild swapped texts + named titles
named_titles, swapped_titles = {}, {}
for a in inwin:
    named_titles[a["url"]] = a["title"]
    st_name = swap[a["ticker"]]
    swapped_titles[a["url"]] = replace_focal(a["title"], a["ticker"], DISPLAY[st_name], st_name)

# 2. firm-specific cue lexicon (data-driven)
firm_tokens = {}   # ticker -> set of tokens in its titles
token_firms = {}   # token -> set of firms whose titles contain it
for a in inwin:
    toks = set(tokenize(a["title"].lower()))
    firm_tokens.setdefault(a["ticker"], set()).update(toks)
    for tk in toks:
        token_firms.setdefault(tk, set()).add(a["ticker"])

STOP = {"stock", "stocks", "shares", "earnings", "beat", "beats", "raise", "raises", "buy", "sell", "top", "best", "big", "new", "high", "low", "falls", "rises", "rose", "dropped", "drop", "gain", "gains", "investors", "investor", "announce", "announces", "quarter", "q3", "q4", "guide", "guidance", "target", "price", "target", "analyst", "analysts", "wall", "street", "market", "markets", "week", "day", "year", "time", "update", "news", "report", "results", "why", "how", "what", "now", "set", "hit", "hits", "miss", "misses", "surge", "surges", "jump", "jumps", "climb", "soar", "soars", "up", "down", "record", "highs", "lows", "estimate", "estimates", "forecast", "forecasts", "outlook", "growth", "revenue", "profit", "profits", "sales", "ai", "stock", "etf", "options", "trade", "trading", "invest", "investing", "money", "cash", "dividend", "dividends", "split", "buyback", "ipo", "etf"}

def cue_lexicon(min_in_firm, max_other_firms=3):
    lex = {}
    for tic in firm_tokens:
        own = set(ALIASES[tic]) | {tic.lower(), DISPLAY[tic].lower()}
        own_tokens = {w.lower() for ph in own for w in re.findall(r"[a-z0-9&']+", ph.lower())}
        c = []
        for tk in firm_tokens[tic]:
            if tk in own or tk in own_tokens or tk in STOP:
                continue
            n_here = sum(1 for a in inwin if a["ticker"] == tic and tk in a["title"].lower())
            if n_here < min_in_firm:
                continue
            n_other = len(token_firms.get(tk, set()) - {tic})
            if n_other > max_other_firms:   # generic finance vocabulary
                continue
            c.append(tk)
        lex[tic] = c
    return lex

def flag_with_lex(lex):
    flagged, hits = {}, {}
    for a in inwin:
        stext = swapped_titles[a["url"]].lower()
        found = [tk for tk in lex[a["ticker"]] if re.search(rf"\b{re.escape(tk)}\b", stext)]
        if found:
            flagged[a["url"]] = found
            hits[a["url"]] = found
    return flagged

lex3 = cue_lexicon(3, max_other_firms=5)
lex2 = cue_lexicon(2, max_other_firms=3)
flag3 = flag_with_lex(lex3)
flag2 = flag_with_lex(lex2)

# highest-precision tier: original name/ticker present as a SUBSTRING in the
# rebuilt swapped text (catches name-variant gaps like "ExxonMobil" that the
# word-boundary verification of session 5 cannot see)
name_variant_leaks = []
for a in inwin:
    stext = swapped_titles[a["url"]].lower()
    # aliases of length >= 4 only, as case-insensitive substrings; short tickers
    # (V, MA, GS...) would otherwise match ordinary words and are excluded
    for alias in [al for al in ALIASES[a["ticker"]] if len(al) >= 4]:
        if alias.lower() in stext:
            name_variant_leaks.append({"url": a["url"], "ticker": a["ticker"], "residual": alias,
                                       "swapped_text": swapped_titles[a["url"]]})
            break

# baseline: share of NAMED titles containing >=1 non-name cue (context only)
def named_cue_share(lex):
    n = 0
    for a in inwin:
        t = a["title"].lower()
        if any(re.search(rf"\b{re.escape(tk)}\b", t) for tk in lex[a["ticker"]]):
            n += 1
    return n / len(inwin)

# 3. re-run key contrasts on unflagged subsample
n5 = load("llm_scores_s5_named.json")
a5 = load("llm_scores_s5_anonv2.json")
s5 = load("llm_scores_s5_swap.json")
BATCH = 25
urls = [a["url"] for a in inwin]
batch_of = {u: i // BATCH for i, u in enumerate(urls)}

def cluster_se(d, batches):
    m = sum(d) / len(d)
    gs = {}
    for v, b in zip(d, batches):
        gs.setdefault(b, []).append(v)
    G = len(gs)
    ss = 0.0
    for b, vals in gs.items():
        s_b = sum(vals) - len(vals) * m
        ss += s_b * s_b
    return math.sqrt(ss / (len(d) ** 2) * G / max(1, G - 1))

def contrast_stats(x, y, keep_urls):
    d = [x[u]["sentiment"] - y[u]["sentiment"] for u in keep_urls]
    bs = [batch_of[u] for u in keep_urls]
    dbar = sum(d) / len(d)
    sd = st.pstdev(d)
    se_hl = sd / math.sqrt(len(d))
    se_cl = cluster_se(d, bs)
    T = 1.6495
    return {
        "n": len(d),
        "mean_diff": round(dbar, 4),
        "t_headline": round(dbar / se_hl, 3),
        "t_cluster": round(dbar / se_cl, 3),
        "ci90_headline": [round(dbar - T * se_hl, 3), round(dbar + T * se_hl, 3)],
        "sd": round(sd, 3),
    }

keep3 = [u for u in urls if u not in flag3]
keep2 = [u for u in urls if u not in flag2]

recheck = {}
for tag, keep in [("excl_cue3", keep3), ("excl_cue2", keep2)]:
    recheck[tag] = {
        "named_minus_swapped": contrast_stats(n5, s5, keep),
        "swapped_minus_anonv2": contrast_stats(s5, a5, keep),
        "named_minus_anonv2": contrast_stats(n5, a5, keep),
    }
recheck["full_sample"] = {
    "named_minus_swapped": contrast_stats(n5, s5, urls),
    "swapped_minus_anonv2": contrast_stats(s5, a5, urls),
    "named_minus_anonv2": contrast_stats(n5, a5, urls),
}

# examples for the report
examples = []
for tic, cues in sorted(lex3.items()):
    if not cues:
        continue
    cnt = {tk: sum(1 for a in inwin if a["ticker"] == tic and tk in a["title"].lower()) for tk in cues}
    top = sorted(cnt.items(), key=lambda kv: -kv[1])[:6]
    examples.append({"ticker": tic, "top_cues": top})

out = {
  "design": {
    "script": "swap_leakage_audit.py", "seed": SEED,
    "method": "data-driven lexical cue lexicon; cue = token in >=3 of firm's in-window titles and in <=5 other firms' titles (primary), or >=2 titles and <=3 other firms (sensitivity); not the firm's own alias/ticker/name variants; finance-generic stoplist excluded; flagged = >=1 original-firm cue token present in the rebuilt swapped text",
    "disclosure": "lexical heuristic, reproducible from archived corpus; not human annotation",
  },
  "n_flagged_primary": len(flag3), "n_flagged_sensitivity": len(flag2),
  "n_name_variant_leaks": len(name_variant_leaks),
  "name_variant_leaks": name_variant_leaks,
  "share_flagged_primary": round(len(flag3) / 341, 4),
  "share_flagged_sensitivity": round(len(flag2) / 341, 4),
  "named_titles_with_cues_share": round(named_cue_share(lex3), 4),
  "contrasts_recheck": recheck,
  "per_firm_examples": examples[:12],
}
with open(f"{DATA}/results_swap_leakage.json", "w") as f:
    json.dump(out, f, indent=1)
with open(f"{DATA}/s6_cue_lexicon.json", "w") as f:
    json.dump({"primary_ge3": lex3, "sensitivity_ge2": lex2}, f, indent=1)

print(f"flagged (primary >=3): {len(flag3)}/341 = {len(flag3)/341:.1%}")
print(f"flagged (sensitivity >=2): {len(flag2)}/341 = {len(flag2)/341:.1%}")
print(f"name-variant substring leaks (highest precision): {len(name_variant_leaks)}/341")
for nv in name_variant_leaks:
    print(f"   [{nv['ticker']}] residual='{nv['residual']}' :: {nv['swapped_text'][:90]}")
print(f"named titles with >=1 non-name cue: {named_cue_share(lex3):.1%}")
print()
for tag in ["full_sample", "excl_cue3", "excl_cue2"]:
    print(f"--- {tag} ---")
    for k, r in recheck[tag].items():
        print(f"  {k:24s} n={r['n']:3d} mean={r['mean_diff']:>7.3f} t_hl={r['t_headline']:>6.2f} t_cl={r['t_cluster']:>6.2f} CI90_hl=[{r['ci90_headline'][0]:.2f},{r['ci90_headline'][1]:.2f}]")
print()
print("sample flagged headlines (primary):")
for u, hs in list(flag3.items())[:8]:
    tic = next(a["ticker"] for a in inwin if a["url"] == u)
    print(f"  [{tic}] {hs[:4]} :: {swapped_titles[u][:95]}")
print("saved -> data/results_swap_leakage.json, data/s6_cue_lexicon.json")
