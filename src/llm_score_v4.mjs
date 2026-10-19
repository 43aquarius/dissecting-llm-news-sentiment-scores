// SESSION 4: mechanism experiment for the batch-composition effect.
//
// Pre-specified design (run order INVERTED relative to session 3 so that
// time-of-session works AGAINST the composition effect):
//   1. v1comp   : all 542 articles in v1 order (composition control), FIRST.
//   2. orig341  : the 341 in-window in the standard (session-2/3) order, SECOND.
//   3. shuf341  : the 341 in a seeded random shuffle, THIRD (re-batch
//                 sensitivity: same headlines, different batch-mates/positions).
//
// If the composition effect (542 minus 341) reproduces with this reversed
// order, time-of-session is ruled out and the effect is batch composition.
// If shuffled ~= original, re-batching within the corpus is inert and the
// effect is specifically the out-of-window mixing; if not, general batch
// sensitivity. Protocol byte-identical to v1/v2/v3. Log: llm_score_v4.log.
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const ALL = '/home/z/my-project/data/news_all.json';
const LOG = '/home/z/my-project/scripts/llm_score_v4.log';
const BATCH = 25;

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

const companyMap = Object.fromEntries(
  [["AAPL","Apple"],["MSFT","Microsoft"],["NVDA","Nvidia"],["GOOGL","Alphabet"],["AMZN","Amazon"],["META","Meta Platforms"],["TSLA","Tesla"],["AVGO","Broadcom"],["AMD","Advanced Micro Devices"],["NFLX","Netflix"],["INTC","Intel"],["ORCL","Oracle"],["CRM","Salesforce"],["ADBE","Adobe"],["QCOM","Qualcomm"],["IBM","IBM"],["JPM","JPMorgan Chase"],["BAC","Bank of America"],["GS","Goldman Sachs"],["MS","Morgan Stanley"],["WFC","Wells Fargo"],["V","Visa"],["MA","Mastercard"],["XOM","Exxon Mobil"],["CVX","Chevron"],["PG","Procter & Gamble"],["KO","Coca-Cola"],["WMT","Walmart"],["COST","Costco"],["JNJ","Johnson & Johnson"],["LLY","Eli Lilly"],["DIS","Disney"],["BA","Boeing"],["CAT","Caterpillar"],["GE","GE Aerospace"],["PFE","Pfizer"]]);

const BACKOFF_MS = [30000, 60000, 90000, 120000, 180000, 300000];

function logline(s) { fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`); }

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

async function runPass(zai, articles, outPath, label) {
  let scores = {};
  try { scores = JSON.parse(fs.readFileSync(outPath, 'utf-8')); } catch {}
  const todo = articles.filter(a => !scores[a.url]);
  logline(`${label}: articles=${articles.length} to_score=${todo.length}`);
  if (todo.length === 0) return;
  const nb = Math.ceil(todo.length / BATCH);
  for (let b = 0; b < nb; b++) {
    const batch = todo.slice(b * BATCH, (b + 1) * BATCH);
    if (batch.length === 0) break;
    const lines = batch.map(a => `id=${a.idx}: [${companyMap[a.ticker] || a.ticker}] ${a.title}`);
    const userMsg = 'Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n' + lines.join('\n');
    let parsed = null, model = '';
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
        parsed = parseScoreResponse(text, batch);
        model = completion.model || completion.id || '';
        break;
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        logline(`${label} batch=${b} attempt=${attempt} FAIL ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
        await new Promise(r => setTimeout(r, isRate ? BACKOFF_MS[attempt - 1] : 4000));
      }
    }
    if (parsed) {
      Object.assign(scores, parsed);
      fs.writeFileSync(outPath, JSON.stringify(scores, null, 1));
      logline(`${label} batch=${b} ok n=${Object.keys(parsed).length} model=${model}`);
      await new Promise(r => setTimeout(r, 2000));
    } else {
      logline(`${label} batch=${b} SKIPPED after attempts`);
    }
    console.log(`${label}: batch ${b + 1}/${nb} done`);
  }
}

async function main() {
  const zai = await ZAI.create();
  logline('SESSION4 START mode=mechanism runorder=v1comp-then-orig-then-shuffle');

  // 1. v1 composition FIRST (reversed time order vs session 3)
  const articles542 = JSON.parse(fs.readFileSync(ALL, 'utf-8')).map((a, i) => ({ ...a, idx: i }));
  await runPass(zai, articles542, '/home/z/my-project/data/llm_scores_s4_v1comp.json', 'v1comp');

  // 2. original 341 order SECOND
  const articles341 = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
  await runPass(zai, articles341, '/home/z/my-project/data/llm_scores_s4_orig.json', 'orig341');

  // 3. seeded shuffle THIRD (mulberry32, seed 20261018)
  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const shuffled = [...articles341];
  const rng = mulberry32(20261018);
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  fs.writeFileSync('/home/z/my-project/data/s4_shuffle_order.json',
    JSON.stringify(shuffled.map(a => a.url)));
  logline('shuffle: seed=20261018 order saved to data/s4_shuffle_order.json');
  await runPass(zai, shuffled, '/home/z/my-project/data/llm_scores_s4_shuf.json', 'shuf341');

  logline('SESSION4 ALL DONE');
  console.log('SESSION4 ALL DONE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
