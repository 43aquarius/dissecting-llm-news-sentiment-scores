// LLM sentiment scoring of news headlines (Lopez-Lira & Tang 2023 style).
// Batches of 25 headlines per call. Incremental save. Resume support.
// Output: /home/z/my-project/data/llm_scores.json
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const NEWS_PATH = '/home/z/my-project/data/news_all.json';
const OUT_PATH = '/home/z/my-project/data/llm_scores.json';
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

function parseScoreResponse(text, batch) {
  // strip markdown fences if present
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

async function main() {
  const zai = await ZAI.create();
  const articles = JSON.parse(fs.readFileSync(NEWS_PATH, 'utf-8'));
  let scores = {};
  try { scores = JSON.parse(fs.readFileSync(OUT_PATH, 'utf-8')); } catch {}

  const todo = articles.map((a, i) => ({ ...a, idx: i })).filter(a => !scores[a.url]);
  console.log(`articles: ${articles.length}, to score: ${todo.length}`);
  if (todo.length === 0) { console.log('all scored'); return; }

  const companies = {};
  for (const a of articles) companies[a.ticker] = companies[a.ticker] || a.title;

  const universe = [["AAPL","Apple"],["MSFT","Microsoft"],["NVDA","Nvidia"],["GOOGL","Alphabet"],["AMZN","Amazon"],["META","Meta Platforms"],["TSLA","Tesla"],["AVGO","Broadcom"],["AMD","Advanced Micro Devices"],["NFLX","Netflix"],["INTC","Intel"],["ORCL","Oracle"],["CRM","Salesforce"],["ADBE","Adobe"],["QCOM","Qualcomm"],["IBM","IBM"],["JPM","JPMorgan Chase"],["BAC","Bank of America"],["GS","Goldman Sachs"],["MS","Morgan Stanley"],["WFC","Wells Fargo"],["V","Visa"],["MA","Mastercard"],["XOM","Exxon Mobil"],["CVX","Chevron"],["PG","Procter & Gamble"],["KO","Coca-Cola"],["WMT","Walmart"],["COST","Costco"],["JNJ","Johnson & Johnson"],["LLY","Eli Lilly"],["DIS","Disney"],["BA","Boeing"],["CAT","Caterpillar"],["GE","GE Aerospace"],["PFE","Pfizer"]];
  const companyMap = Object.fromEntries(universe);

  let done = 0;
  for (let bs = 0; bs < todo.length; bs += BATCH) {
    const batch = todo.slice(bs, bs + BATCH);
    const lines = batch.map(a => `id=${a.idx}: [${companyMap[a.ticker] || a.ticker}] ${a.title}`);
    const userMsg = `Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n${lines.join('\n')}`;

    let parsed = null;
    for (let attempt = 1; attempt <= 3; attempt++) {
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
        break;
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        console.log(`  batch ${bs / BATCH}: attempt ${attempt} failed ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 70)}`);
        if (isRate) await new Promise(r => setTimeout(r, 30000));
        else await new Promise(r => setTimeout(r, 3000));
      }
    }
    if (parsed) {
      Object.assign(scores, parsed);
      fs.writeFileSync(OUT_PATH, JSON.stringify(scores, null, 1));
      done += Object.keys(parsed).length;
      console.log(`progress: ${done}/${todo.length} scored`);
    } else {
      console.log(`  batch ${bs / BATCH} SKIPPED after 3 attempts`);
    }
  }
  console.log(`DONE: ${Object.keys(scores).length} scored of ${articles.length}`);
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 200)); process.exit(1); });
