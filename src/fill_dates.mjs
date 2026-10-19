// Fill missing publication dates via z-ai page_reader (server-side, gets publishedTime).
// Processes undated articles from ws_news.json. Concurrency 3, incremental save.
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const NEWS_PATH = '/home/z/my-project/data/ws_news_clean.json';
const FAIL_PATH = '/home/z/my-project/data/ws_pr_failed.json';

function parseDate(s) {
  if (!s) return null;
  s = String(s).trim();
  let m;
  // ISO: 2026-08-15...
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  // "Oct 14, 2026" / "Aug 1, 2026"
  const months = { Jan:1,Feb:2,Mar:3,Apr:4,May:5,Jun:6,Jul:7,Aug:8,Sep:9,Oct:10,Nov:11,Dec:12 };
  m = s.match(/^([A-Za-z]{3})[a-z]*\s+(\d{1,2}),?\s+(\d{4})/);
  if (m && months[m[1]]) {
    const mo = String(months[m[1]]).padStart(2, '0');
    const d = String(parseInt(m[2])).padStart(2, '0');
    return `${m[3]}-${mo}-${d}`;
  }
  // ISO datetime: 2026-08-15T...
  m = s.match(/^(\d{4})-(\d{2})-(\d{2})T/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  return null;
}

async function main() {
  const zai = await ZAI.create();
  const articles = JSON.parse(fs.readFileSync(NEWS_PATH, 'utf-8'));
  let failed = {};
  try { failed = JSON.parse(fs.readFileSync(FAIL_PATH, 'utf-8')); } catch {}

  const todo = articles.map((a, i) => ({ a, i }))
    .filter(({ a }) => !parseDate(a.date) && !failed[a.url]);

  console.log(`undated articles to process: ${todo.length}`);
  if (todo.length === 0) { console.log('nothing to do'); return; }

  const CONC = 3;
  let processed = 0, gotDates = 0;
  const t0 = Date.now();

  async function processOne({ a, i }) {
    for (let attempt = 1; attempt <= 2; attempt++) {
      try {
        const r = await zai.functions.invoke('page_reader', { url: a.url });
        const data = r.data || r;
        const pt = data.publishedTime || data.publish_time || data.published_time || '';
        const d = parseDate(pt) || parseDate(data.title || '');
        if (d) {
          a.date = d;
          if (!a.title || a.title.length < 10) a.title = (data.title || a.title).trim();
          gotDates++;
        } else {
          failed[a.url] = 'no-date';
        }
        return;
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        if (isRate) {
          await new Promise(r => setTimeout(r, 25000));
          if (attempt === 1) attempt++; // one extra try after rate wait
        } else {
          failed[a.url] = 'error:' + String(e).slice(0, 60);
          return;
        }
      }
    }
    failed[a.url] = 'rate-limit-skipped';
  }

  for (let batchStart = 0; batchStart < todo.length; batchStart += CONC * 4) {
    const batch = todo.slice(batchStart, batchStart + CONC * 4);
    const groups = [];
    for (let i = 0; i < batch.length; i += CONC) groups.push(batch.slice(i, i + CONC));
    for (const g of groups) {
      await Promise.all(g.map(processOne));
      processed += g.length;
    }
    fs.writeFileSync(NEWS_PATH, JSON.stringify(articles, null, 1));
    fs.writeFileSync(FAIL_PATH, JSON.stringify(failed, null, 1));
    const elapsed = Math.round((Date.now() - t0) / 1000);
    console.log(`progress: ${processed}/${todo.length} (dates: ${gotDates}) [${elapsed}s]`, );
  }
  console.log(`DONE: got dates for ${gotDates}/${todo.length}`);
}

main().catch(e => { console.error('FATAL', e); process.exit(1); });
