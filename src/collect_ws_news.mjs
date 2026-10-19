// Collect firm-specific news headlines via z-ai web_search (server-side).
// 36 firms x 5 query templates. Incremental JSONL saving. Resume support.
// Output: /home/z/my-project/data/ws_news.json + /home/z/my-project/data/ws_progress.json
const fs = await import('fs');
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

const NEWS_PATH = '/home/z/my-project/data/ws_news.json';
const PROG_PATH = '/home/z/my-project/data/ws_progress.json';

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

function queriesFor(ticker, company) {
  return [
    `${company} ${ticker} stock news`,
    `${company} stock July 2026`,
    `${company} stock August 2026`,
    `${company} stock September 2026`,
    `${company} stock October 2026`,
  ];
}

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
        const r = await zai.functions.invoke('web_search', { query: q, num: 20 });
        items = Array.isArray(r) ? r : (r.data || r.results || []);
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        console.log(`  ERR ${ticker} [${isRate ? 'RATE' : 'FAIL'}]: ${String(e).slice(0, 60)}`);
        if (isRate) {
          // do NOT mark done; wait long and retry later
          await new Promise(r => setTimeout(r, 30000));
          continue;
        }
      }
      if (items === null) { done.add(key); saveState(articles, done); continue; }
      let added = 0;
      for (const item of items) {
        const url = item.url || '';
        const title = (item.name || '').trim();
        if (!url || !title) continue;
        if (articles.some(a => a.url === url)) continue;
        // relevance filter: title mentions company or ticker
        const t = title.toLowerCase();
        const cl = company.toLowerCase();
        const tl = ticker.toLowerCase();
        const mentions = t.includes(cl) || t.includes(tl + ' ') || t.includes(`(${ticker.toLowerCase()})`) || t.includes(`(${ticker.toLowerCase()}`) ;
        if (!mentions) continue;
        articles.push({
          ticker, url, title,
          date: item.date || '',
          domain: item.host_name || '',
          source_query: q,
        });
        added++;
      }
      firmAdded += added;
      done.add(key);
      saveState(articles, done);
      await new Promise(r => setTimeout(r, 1500));
    }
    console.log(`[${fi + 1}/${FIRMS.length}] ${ticker}: +${firmAdded} (total ${articles.length})`);
  }
  console.log(`DONE: ${articles.length} articles`);
}

main().catch(e => { console.error('FATAL', e); process.exit(1); });
