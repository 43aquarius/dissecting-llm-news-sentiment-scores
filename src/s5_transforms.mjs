// Shared text transformations for session 5 (imported by llm_score_v5.mjs and dryrun_s5.mjs).
// CORRECTED alias table: adds "Visa" for ticker V (the disclosed session-1/2 anonymization gap).
import fs from 'fs';

export const SYSTEM_PROMPT = `You are an expert financial analyst specialized in news sentiment analysis for equity research. You evaluate how news headlines affect a company's stock value.

For each headline you must return:
- "sentiment": integer from -100 to +100. -100 = extremely negative impact on the company's stock value; 0 = neutral or no clear impact; +100 = extremely positive impact. Judge from the perspective of a shareholder of the company.
- "relevance": integer from 0 to 100. 100 = headline is directly about the company's business, earnings, products, guidance, or stock; 0 = headline mentions the company only incidentally or is a generic market/quote page.

Rules:
- Base your judgment ONLY on the information in the headline text.
- Earnings beats, raised guidance, product launches, upgrades, buybacks = positive.
- Earnings misses, cut guidance, lawsuits, recalls, downgrades, layoffs = negative.
- Speculation or rumor framing lowers the magnitude toward zero.
- Generic quote pages, price summaries without direction, or calendar pages = sentiment 0, relevance low.

Return ONLY a valid JSON array. One object per headline, in the same order as given, with fields: "id", "sentiment", "relevance". No other text.`;

export const ALIASES = {
  AAPL: ["Apple"], MSFT: ["Microsoft"], NVDA: ["Nvidia", "NVIDIA"], GOOGL: ["Alphabet", "Google"],
  AMZN: ["Amazon"], META: ["Meta Platforms", "Meta", "Facebook"], TSLA: ["Tesla"], AVGO: ["Broadcom"],
  AMD: ["Advanced Micro Devices", "AMD"], NFLX: ["Netflix"], INTC: ["Intel"], ORCL: ["Oracle"],
  CRM: ["Salesforce"], ADBE: ["Adobe"], QCOM: ["Qualcomm"], IBM: ["IBM"],
  JPM: ["JPMorgan Chase", "JPMorgan", "J.P. Morgan"], BAC: ["Bank of America", "BofA"],
  GS: ["Goldman Sachs"], MS: ["Morgan Stanley"], WFC: ["Wells Fargo"], V: ["Visa"],
  MA: ["Mastercard"], XOM: ["Exxon Mobil", "Exxon"], CVX: ["Chevron"], PG: ["Procter & Gamble", "P&G"],
  KO: ["Coca-Cola", "Coca Cola", "Coke"], WMT: ["Walmart", "Wal-Mart"], COST: ["Costco"],
  JNJ: ["Johnson & Johnson", "Johnson and Johnson"], LLY: ["Eli Lilly", "Lilly"], DIS: ["Disney"],
  BA: ["Boeing"], CAT: ["Caterpillar"], GE: ["GE Aerospace", "General Electric"], PFE: ["Pfizer"],
};

export const DISPLAY = {
  AAPL: "Apple", MSFT: "Microsoft", NVDA: "Nvidia", GOOGL: "Alphabet", AMZN: "Amazon",
  META: "Meta Platforms", TSLA: "Tesla", AVGO: "Broadcom", AMD: "Advanced Micro Devices",
  NFLX: "Netflix", INTC: "Intel", ORCL: "Oracle", CRM: "Salesforce", ADBE: "Adobe",
  QCOM: "Qualcomm", IBM: "IBM", JPM: "JPMorgan Chase", BAC: "Bank of America", GS: "Goldman Sachs",
  MS: "Morgan Stanley", WFC: "Wells Fargo", V: "Visa", MA: "Mastercard", XOM: "Exxon Mobil",
  CVX: "Chevron", PG: "Procter & Gamble", KO: "Coca-Cola", WMT: "Walmart", COST: "Costco",
  JNJ: "Johnson & Johnson", LLY: "Eli Lilly", DIS: "Disney", BA: "Boeing", CAT: "Caterpillar",
  GE: "GE Aerospace", PFE: "Pfizer",
};

export const TICKERS = Object.keys(ALIASES);

const esc = s => s.replace(/[.*+?^${}()|[\]\\&]/g, '\\$&');

function focalIdentifiers(ticker) {
  return [...(ALIASES[ticker] || [])].sort((a, b) => b.length - a.length).map(n => ({ kind: 'alias', token: n }));
}

export function replaceFocal(title, ticker, replacementName, replacementTicker) {
  let t = title;
  for (const { token } of focalIdentifiers(ticker)) {
    // case-insensitive like the anonymized condition (handles ALL-CAPS/possessive forms)
    t = t.replace(new RegExp(`\\b${esc(token)}\\b`, 'gi'), replacementName);
  }
  t = t.replace(new RegExp(`\\b${ticker}\\b`, 'g'), replacementTicker); // case-sensitive
  t = t.replace(new RegExp(`\\b${replacementName}( ${replacementName})+\\b`, 'g'), replacementName);
  return t;
}

export function anonymizeV2(title, ticker) {
  let t = title;
  t = t.replace(new RegExp(`\\b${ticker}\\b`, 'g'), 'the company');
  for (const { token } of focalIdentifiers(ticker)) {
    t = t.replace(new RegExp(`\\b${esc(token)}\\b`, 'gi'), 'the company');
  }
  t = t.replace(/\bthe company( the company)+\b/gi, 'the company');
  t = t.replace(/(^|\.\s+)the company/g, (m, p1) => `${p1}The company`);
  return t;
}

export function verifyNoFocal(title, ticker) {
  const hits = [];
  if (new RegExp(`\\b${ticker}\\b`).test(title)) hits.push(ticker);
  for (const { token } of focalIdentifiers(ticker)) {
    if (new RegExp(`\\b${esc(token)}\\b`, 'i').test(title)) hits.push(token);
  }
  return hits;
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function buildSwapMap(seed = 20261019, path = '/home/z/my-project/data/s5_swap_map.json') {
  try { return JSON.parse(fs.readFileSync(path, 'utf-8')); } catch {}
  const rnd = mulberry32(seed);
  let map;
  for (let guard = 0; guard < 10000; guard++) {
    const arr = [...TICKERS];
    for (let i = arr.length - 1; i > 0; i--) {
      const j = Math.floor(rnd() * (i + 1));
      [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    map = Object.fromEntries(TICKERS.map((t, i) => [t, arr[i]]));
    if (TICKERS.every(t => map[t] !== t)) break;
  }
  fs.writeFileSync(path, JSON.stringify(map, null, 1));
  return map;
}
