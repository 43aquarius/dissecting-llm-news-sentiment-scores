// AUDIT experiments (v2): anonymized scoring + repeat-call stability.
//
// Conditions (all on the SAME 341 in-window headlines):
//   anon  : company names/tickers replaced by "the company", no [Company] prefix.
//           Everything else identical to the original protocol (same system prompt).
//   rep1..rep3 : the ORIGINAL named protocol repeated 3 independent times.
// Outputs: data/llm_scores_anon.json, data/llm_scores_rep{1,2,3}.json
// Log:     scripts/llm_score_v2.log (timestamps, batch ids, raw response snippets)
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const IN_PATH = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v2.log';
const BATCH = 25;

// same system prompt as the original protocol (verbatim)
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
  // ticker: exact word, case-sensitive (all caps)
  t = t.replace(new RegExp(`\\b${ticker}\\b`, 'g'), 'the company');
  // company names / aliases: case-insensitive
  for (const name of ALIASES[ticker] || []) {
    const esc = name.replace(/[.*+?^${}()|[\]\\&]/g, '\\$&');
    t = t.replace(new RegExp(`\\b${esc}\\b`, 'gi'), 'the company');
  }
  // de-duplicate "the company the company"
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

async function runCondition(zai, articles, outPath, condition) {
  let scores = {};
  try { scores = JSON.parse(fs.readFileSync(outPath, 'utf-8')); } catch {}
  const todo = articles.filter(a => !scores[a.url]);
  logline(`condition=${condition}: articles=${articles.length} to_score=${todo.length}`);
  console.log(`${condition}: ${todo.length} to score`);
  if (todo.length === 0) return;

  const companies = {};
  for (const a of articles) companies[a.ticker] = true;
  const companyMap = Object.fromEntries(
    [["AAPL","Apple"],["MSFT","Microsoft"],["NVDA","Nvidia"],["GOOGL","Alphabet"],["AMZN","Amazon"],["META","Meta Platforms"],["TSLA","Tesla"],["AVGO","Broadcom"],["AMD","Advanced Micro Devices"],["NFLX","Netflix"],["INTC","Intel"],["ORCL","Oracle"],["CRM","Salesforce"],["ADBE","Adobe"],["QCOM","Qualcomm"],["IBM","IBM"],["JPM","JPMorgan Chase"],["BAC","Bank of America"],["GS","Goldman Sachs"],["MS","Morgan Stanley"],["WFC","Wells Fargo"],["V","Visa"],["MA","Mastercard"],["XOM","Exxon Mobil"],["CVX","Chevron"],["PG","Procter & Gamble"],["KO","Coca-Cola"],["WMT","Walmart"],["COST","Costco"],["JNJ","Johnson & Johnson"],["LLY","Eli Lilly"],["DIS","Disney"],["BA","Boeing"],["CAT","Caterpillar"],["GE","GE Aerospace"],["PFE","Pfizer"]]);

  let done = 0;
  for (let bs = 0; bs < todo.length; bs += BATCH) {
    const batch = todo.slice(bs, bs + BATCH).map((a, i) => ({ ...a, idx: bs + i }));
    // condition-specific user message
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

    let parsed = null;
    for (let attempt = 1; attempt <= 4; attempt++) {
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
        logline(`condition=${condition} batch=${bs / BATCH} attempt=${attempt} ok n=${Object.keys(parsed).length} raw="${String(text).slice(0, 120).replace(/\n/g, ' ')}"`);
        break;
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        logline(`condition=${condition} batch=${bs / BATCH} attempt=${attempt} FAIL ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
        await new Promise(r => setTimeout(r, isRate ? 30000 : 3000));
      }
    }
    if (parsed) {
      Object.assign(scores, parsed);
      fs.writeFileSync(outPath, JSON.stringify(scores, null, 1));
      done += Object.keys(parsed).length;
      console.log(`  ${condition}: ${done}/${todo.length}`);
    } else {
      logline(`condition=${condition} batch=${bs / BATCH} SKIPPED after 4 attempts`);
    }
  }
}

async function main() {
  const zai = await ZAI.create();
  const articles = JSON.parse(fs.readFileSync(IN_PATH, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
  // build anonymized titles
  for (const a of articles) a.anon_title = anonymize(a.title, a.ticker);
  // sanity: how many titles actually contained an identifier?
  const changed = articles.filter(a => a.anon_title !== a.title).length;
  console.log(`in-window articles: ${articles.length}; titles containing an identifier: ${changed}`);
  logline(`START v2: in_window=${articles.length} changed_by_anon=${changed}`);
  // sample
  console.log('sample anonymizations:');
  for (const a of articles.slice(0, 3)) console.log(`  "${a.title}" -> "${a.anon_title}"`);

  await runCondition(zai, articles, '/home/z/my-project/data/llm_scores_anon.json', 'anon');
  for (const rep of ['rep1', 'rep2', 'rep3']) {
    await runCondition(zai, articles, `/home/z/my-project/data/llm_scores_${rep}.json`, rep);
  }
  logline('ALL DONE');
  console.log('ALL DONE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
