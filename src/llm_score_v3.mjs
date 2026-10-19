// SESSION 3 experiments (P1-2 + P1-3), all in ONE session, interleaved.
//
// Design (pre-registered):
//   P1-2  Same-session interleaved identity pairing:
//         - SAME 341 in-window headlines as session 2 (news_scored.json order).
//         - 4 rounds; each round walks the 14 batches (25/batch).
//           For even batch: call NAMED then ANON. For odd batch: ANON then NAMED.
//           (order alternation balances any monotonic within-session drift)
//         - Outputs data/llm_scores_s3_named_r{k}.json / llm_scores_s3_anon_r{k}.json
//   P1-3  Batch-composition control (drift source):
//         - The FULL 542 articles in news_all.json order, batches of 25,
//           NAMED protocol, 1 round — replicating the v1 batch composition.
//           Restricting its scores to the 341 in-window URLs and comparing to
//           the s3 341-composition named rounds isolates the COMPOSITION effect
//           within a single session (same endpoint state).
//         - Output data/llm_scores_s3_v1comp.json
//
// Protocol is byte-identical to v1/v2 (same system prompt, same [Company]
// prefix for named, same anonymize() for anon, thinking disabled, batch 25).
// Log: scripts/llm_score_v3.log (ISO timestamps, model id, batch ids).
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const ALL = '/home/z/my-project/data/news_all.json';
const LOG = '/home/z/my-project/scripts/llm_score_v3.log';
const BATCH = 25;
const ROUNDS = 4;

const SYSTEM_PROMPT = `You are an expert financial analyst specialized in news sentiment analysis for equity research. You evaluate how news headlines affect a company's stock value.

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

const ALIASES = {
  AAPL: ["Apple"], MSFT: ["Microsoft"], NVDA: ["Nvidia", "NVIDIA"], GOOGL: ["Alphabet", "Google"],
  AMZN: ["Amazon"], META: ["Meta Platforms", "Meta", "Facebook"], TSLA: ["Tesla"], AVGO: ["Broadcom"],
  AMD: ["Advanced Micro Devices", "AMD"], NFLX: ["Netflix"], INTC: ["Intel"], ORCL: ["Oracle"],
  CRM: ["Salesforce"], ADBE: ["Adobe"], QCOM: ["Qualcomm"], IBM: ["IBM"],
  JPM: ["JPMorgan Chase", "JPMorgan", "J.P. Morgan"], BAC: ["Bank of America", "BofA"],
  GS: ["Goldman Sachs"], MS: ["Morgan Stanley"], WFC: ["Wells Fargo"], V: [],
  MA: ["Mastercard"], XOM: ["Exxon Mobil", "Exxon"], CVX: ["Chevron"], PG: ["Procter & Gamble", "P&G"],
  KO: ["Coca-Cola", "Coca Cola", "Coke"], WMT: ["Walmart", "Wal-Mart"], COST: ["Costco"],
  JNJ: ["Johnson & Johnson", "Johnson and Johnson"], LLY: ["Eli Lilly", "Lilly"], DIS: ["Disney"],
  BA: ["Boeing"], CAT: ["Caterpillar"], GE: ["GE Aerospace", "General Electric"], PFE: ["Pfizer"],
};

function anonymize(title, ticker) {
  let t = title;
  t = t.replace(new RegExp(`\\b${ticker}\\b`, 'g'), 'the company');
  for (const name of ALIASES[ticker] || []) {
    const esc = name.replace(/[.*+?^${}()|[\]\\&]/g, '\\$&');
    t = t.replace(new RegExp(`\\b${esc}\\b`, 'gi'), 'the company');
  }
  t = t.replace(/\bthe company( the company)+\b/gi, 'the company');
  return t;
}

function logline(s) {
  fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`);
}

function parseScoreResponse(text, batch) {
  let t = String(text).replace(/```json|```/g, '').trim();
  const start = t.indexOf('[');
  const end = t.lastIndexOf(']');
  if (start === -1 || end === -1) throw new Error('no JSON array found');
  t = t.slice(start, end + 1);
  const arr = JSON.parse(t);
  const out = {};
  for (const o of arr) {
    const id = parseInt(o.id);
    if (isNaN(id)) continue;
    const s = Math.max(-100, Math.min(100, parseInt(o.sentiment)));
    const r = Math.max(0, Math.min(100, parseInt(o.relevance)));
    const art = batch.find(a => a.idx === id);
    if (art) out[art.url] = { sentiment: s, relevance: r };
  }
  return out;
}

const companyMap = Object.fromEntries(
  [["AAPL","Apple"],["MSFT","Microsoft"],["NVDA","Nvidia"],["GOOGL","Alphabet"],["AMZN","Amazon"],["META","Meta Platforms"],["TSLA","Tesla"],["AVGO","Broadcom"],["AMD","Advanced Micro Devices"],["NFLX","Netflix"],["INTC","Intel"],["ORCL","Oracle"],["CRM","Salesforce"],["ADBE","Adobe"],["QCOM","Qualcomm"],["IBM","IBM"],["JPM","JPMorgan Chase"],["BAC","Bank of America"],["GS","Goldman Sachs"],["MS","Morgan Stanley"],["WFC","Wells Fargo"],["V","Visa"],["MA","Mastercard"],["XOM","Exxon Mobil"],["CVX","Chevron"],["PG","Procter & Gamble"],["KO","Coca-Cola"],["WMT","Walmart"],["COST","Costco"],["JNJ","Johnson & Johnson"],["LLY","Eli Lilly"],["DIS","Disney"],["BA","Boeing"],["CAT","Caterpillar"],["GE","GE Aerospace"],["PFE","Pfizer"]]);

const BACKOFF_MS = [30000, 60000, 90000, 120000, 180000, 300000];

async function callBatch(zai, batch, condition) {
  let lines;
  if (condition === 'anon') {
    lines = batch.map(a => `id=${a.idx}: ${a.anon_title}`);
  } else {
    lines = batch.map(a => `id=${a.idx}: [${companyMap[a.ticker] || a.ticker}] ${a.title}`);
  }
  const userMsg = (condition === 'anon'
    ? 'Headlines (each refers to a single unnamed company):\n\n'
    : 'Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n')
    + lines.join('\n');
  for (let attempt = 1; attempt <= BACKOFF_MS.length; attempt++) {
    try {
      const completion = await zai.chat.completions.create({
        messages: [
          { role: 'assistant', content: SYSTEM_PROMPT },
          { role: 'user', content: userMsg },
        ],
        thinking: { type: 'disabled' },
      });
      const text = completion.choices[0]?.message?.content || '';
      const parsed = parseScoreResponse(text, batch);
      return { parsed, model: completion.model || completion.id || '' };
    } catch (e) {
      const isRate = String(e).includes('429') || String(e).includes('Too many');
      logline(`call FAIL ${condition} n=${batch.length} attempt=${attempt} ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
      await new Promise(r => setTimeout(r, isRate ? BACKOFF_MS[attempt - 1] : 4000));
    }
  }
  return null;
}

async function runInterleaved(zai, articles) {
  // articles: the 341 in-window with anon_title, idx assigned 0..340
  const nb = Math.ceil(articles.length / BATCH);
  for (let r = 1; r <= ROUNDS; r++) {
    const namedPath = `/home/z/my-project/data/llm_scores_s3_named_r${r}.json`;
    const anonPath = `/home/z/my-project/data/llm_scores_s3_anon_r${r}.json`;
    let named = {}; try { named = JSON.parse(fs.readFileSync(namedPath, 'utf-8')); } catch {}
    let anon = {}; try { anon = JSON.parse(fs.readFileSync(anonPath, 'utf-8')); } catch {}
    const roundTodo = articles.filter(a => !named[a.url] || !anon[a.url]);
    logline(`round=${r}: remaining=${roundTodo.length}`);
    if (roundTodo.length === 0) continue;
    for (let b = 0; b < nb; b++) {
      const batch = articles.slice(b * BATCH, (b + 1) * BATCH);
      if (batch.length === 0) break;
      const needNamed = batch.some(a => !named[a.url]);
      const needAnon = batch.some(a => !anon[a.url]);
      if (!needNamed && !needAnon) continue;
      // order alternation: even batch named->anon, odd batch anon->named
      const first = (b % 2 === 0) ? 'named' : 'anon';
      const second = (b % 2 === 0) ? 'anon' : 'named';
      for (const cond of [first, second]) {
        const target = cond === 'named' ? named : anon;
        const path = cond === 'named' ? namedPath : anonPath;
        const need = cond === 'named' ? needNamed : needAnon;
        if (!need) continue;
        const res = await callBatch(zai, batch, cond);
        if (res) {
          Object.assign(target, res.parsed);
          fs.writeFileSync(path, JSON.stringify(target, null, 1));
          logline(`round=${r} batch=${b} cond=${cond} ok n=${Object.keys(res.parsed).length} model=${res.model}`);
          await new Promise(r => setTimeout(r, 2000)); // throttle between calls
        } else {
          logline(`round=${r} batch=${b} cond=${cond} SKIPPED after attempts`);
        }
      }
      console.log(`round ${r}: batch ${b + 1}/${nb} done`);
    }
    logline(`round=${r} COMPLETE named=${Object.keys(named).length} anon=${Object.keys(anon).length}`);
  }
}

async function runV1Composition(zai, articles542) {
  const outPath = '/home/z/my-project/data/llm_scores_s3_v1comp.json';
  let scores = {}; try { scores = JSON.parse(fs.readFileSync(outPath, 'utf-8')); } catch {}
  const todo = articles542.filter(a => !scores[a.url]);
  logline(`v1comp: articles=${articles542.length} to_score=${todo.length}`);
  if (todo.length === 0) return;
  const nb = Math.ceil(todo.length / BATCH);
  for (let b = 0; b < nb; b++) {
    const batch = todo.slice(b * BATCH, (b + 1) * BATCH);
    if (batch.length === 0) break;
    const res = await callBatch(zai, batch, 'named');
    if (res) {
      Object.assign(scores, res.parsed);
      fs.writeFileSync(outPath, JSON.stringify(scores, null, 1));
      logline(`v1comp batch=${b} ok n=${Object.keys(res.parsed).length} model=${res.model}`);
    } else {
      logline(`v1comp batch=${b} SKIPPED after 6 attempts`);
    }
    console.log(`v1comp: batch ${b + 1}/${nb} done`);
  }
}

async function main() {
  const mode = process.argv[2] || 'all'; // 'all' | 'rounds' | 'v1comp'
  const zai = await ZAI.create();
  logline(`SESSION3 START mode=${mode} protocol=identical-v1v2 rounds=${ROUNDS}`);

  if (mode === 'all' || mode === 'rounds') {
    // 341 in-window, same order as session 2 (news_scored.json filtered)
    const articles = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
      .map((a, i) => ({ ...a, idx: i }))
      .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
    for (const a of articles) a.anon_title = anonymize(a.title, a.ticker);
    logline(`s3 in_window=${articles.length}`);
    await runInterleaved(zai, articles);
  }

  if (mode === 'all' || mode === 'v1comp') {
    // P1-3: v1 batch composition = news_all.json order over all 542
    const articles542 = JSON.parse(fs.readFileSync(ALL, 'utf-8'))
      .map((a, i) => ({ ...a, idx: i }));
    await runV1Composition(zai, articles542);
  }

  logline('SESSION3 ALL DONE');
  console.log('SESSION3 ALL DONE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
