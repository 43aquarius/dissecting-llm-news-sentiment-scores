// Enrichment round: event-based queries to add dated news articles.
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const FIRMS = [
  ["AAPL", "Apple"], ["MSFT", "Microsoft"], ["NVDA", "Nvidia"], ["GOOGL", "Google"],
  ["AMZN", "Amazon"], ["META", "Meta"], ["TSLA", "Tesla"], ["AVGO", "Broadcom"],
  ["AMD", "AMD"], ["NFLX", "Netflix"], ["INTC", "Intel"], ["ORCL", "Oracle"],
  ["CRM", "Salesforce"], ["ADBE", "Adobe"], ["QCOM", "Qualcomm"], ["IBM", "IBM"],
  ["JPM", "JPMorgan"], ["BAC", "Bank of America"], ["GS", "Goldman Sachs"], ["MS", "Morgan Stanley"],
  ["WFC", "Wells Fargo"], ["V", "Visa"], ["MA", "Mastercard"], ["XOM", "Exxon"],
  ["CVX", "Chevron"], ["PG", "Procter & Gamble"], ["KO", "Coca-Cola"], ["WMT", "Walmart"],
  ["COST", "Costco"], ["JNJ", "Johnson & Johnson"], ["LLY", "Eli Lilly"], ["DIS", "Disney"],
  ["BA", "Boeing"], ["CAT", "Caterpillar"], ["GE", "GE Aerospace"], ["PFE", "Pfizer"],
];

const NEWS_PATH = '/home/z/my-project/data/ws_news_enrich.json';
const PROG_PATH = '/home/z/my-project/data/ws_enrich_progress.json';

function loadState() {
  let articles = [];
  try { articles = JSON.parse(fs.readFileSync(NEWS_PATH, 'utf-8')); } catch {}
  let done = [];
  try { done = JSON.parse(fs.readFileSync(PROG_PATH, 'utf-8')).done || []; } catch {}
  return { articles, done: new Set(done) };
}
function saveState(articles, done) {
  fs.writeFileSync(NEWS_PATH, JSON.stringify(articles, null, 1));
  fs.writeFileSync(PROG_PATH, JSON.stringify({ done: [...done] }));
}

const queriesFor = (ticker, company) => [
  `${company} quarterly earnings 2026`,
  `${company} stock drops OR rises OR jumps`,
  `site:reuters.com ${company}`,
  `${company} analyst upgrade OR downgrade price target 2026`,
];

async function main() {
  const zai = await ZAI.create();
  const { articles, done } = loadState();
  console.log(`resume: ${articles.length} articles, ${done.size} queries done`);
  for (let fi = 0; fi < FIRMS.length; fi++) {
    const [ticker, company] = FIRMS[fi];
    let firmAdded = 0;
    for (const q of queriesFor(ticker, company)) {
      const key = `${ticker}::${q}`;
      if (done.has(key)) continue;
      let items = null;
      try {
        const r = await zai.functions.invoke('web_search', { query: q, num: 15 });
        items = Array.isArray(r) ? r : (r.data || r.results || []);
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        if (isRate) { await new Promise(r => setTimeout(r, 25000)); continue; }
        console.log(`  ERR ${ticker}: ${String(e).slice(0, 60)}`);
      }
      if (items === null) { done.add(key); saveState(articles, done); continue; }
      let added = 0;
      for (const item of items) {
        const url = item.url || '';
        const title = (item.name || '').trim();
        if (!url || !title) continue;
        if (!item.date) continue;  // enrichment round: DATED results only
        if (articles.some(a => a.url === url)) continue;
        const t = title.toLowerCase();
        if (!t.includes(company.toLowerCase()) && !t.includes(ticker.toLowerCase())) continue;
        articles.push({ ticker, url, title, date: item.date, domain: item.host_name || '', source_query: q });
        added++;
      }
      firmAdded += added;
      done.add(key);
      saveState(articles, done);
      await new Promise(r => setTimeout(r, 1200));
    }
    console.log(`[${fi + 1}/${FIRMS.length}] ${ticker}: +${firmAdded} (total ${articles.length})`);
  }
  console.log(`DONE: ${articles.length}`);
}
main().catch(e => { console.error('FATAL', String(e).slice(0, 200)); process.exit(1); });
