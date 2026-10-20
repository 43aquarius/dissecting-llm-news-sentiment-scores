// Quick single-probe attempt for session-5 completion (environment kills long
// background runners). Behavior: probe quota ONCE; if blocked, exit immediately
// (cheap); if open, run ALL remaining session-5 calls (same protocol/backoff as
// the resume runner) and then exit. Intended to be invoked repeatedly from the
// shell between other work. Resume-safe checkpoints shared with llm_score_v5.mjs.
import fs from 'fs';
import { SYSTEM_PROMPT, DISPLAY, TICKERS, replaceFocal, anonymizeV2, verifyNoFocal, buildSwapMap } from './s5_transforms.mjs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v5.log';
const BATCH = 25;
const SEED = 20261019;
const CALL_BACKOFF_MS = [30000, 60000, 120000, 240000, 480000];

function logline(s) { fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`); }

function parseScoreResponse(text, batch) {
  let t = String(text).replace(/```json|```/g, '').trim();
  const start = t.indexOf('['), end = t.lastIndexOf(']');
  if (start === -1 || end === -1) throw new Error('no JSON array found');
  const arr = JSON.parse(t.slice(start, end + 1));
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

const CONDITIONS = [
  { tag: 'N5', file: 'llm_scores_s5_named.json', decoding: 'default', framed: 'named' },
  { tag: 'A5', file: 'llm_scores_s5_anonv2.json', decoding: 'default', framed: 'anon' },
  { tag: 'S5', file: 'llm_scores_s5_swap.json', decoding: 'default', framed: 'named' },
  { tag: 'P5', file: 'llm_scores_s5_placeholder.json', decoding: 'default', framed: 'named' },
  { tag: 'T0a', file: 'llm_scores_s5_t0a.json', decoding: 'temp0', framed: 'named' },
  { tag: 'T0b', file: 'llm_scores_s5_t0b.json', decoding: 'temp0', framed: 'named' },
];

const zai = await ZAI.create();
// ---- gate probe ---------------------------------------------------------
try {
  await zai.chat.completions.create({
    messages: [{ role: 'assistant', content: 'Reply with a JSON array only.' },
               { role: 'user', content: 'id=0: probe\n\nReturn [{"id":0,"sentiment":0,"relevance":0}].' }],
    thinking: { type: 'disabled' },
  });
} catch (e) {
  console.log('ATTEMPT: quota still blocked');
  process.exit(0);
}
logline(`ATTEMPT: quota OPEN, running remaining calls`);

// ---- remaining calls (identical protocol) --------------------------------
const swap = buildSwapMap();
const articles = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
  .map((a, i) => ({ ...a, idx: i }))
  .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
const texts = { N5: {}, A5: {}, S5: {}, P5: {}, T0a: {}, T0b: {} };
for (const a of articles) {
  texts.N5[a.url] = `[${DISPLAY[a.ticker]}] ${a.title}`;
  texts.T0a[a.url] = texts.N5[a.url];
  texts.T0b[a.url] = texts.N5[a.url];
  const anon = anonymizeV2(a.title, a.ticker);
  texts.A5[a.url] = anon;
  texts.P5[a.url] = `[Company X] ${anon}`;
  const st = swap[a.ticker];
  texts.S5[a.url] = `[${DISPLAY[st]}] ${replaceFocal(a.title, a.ticker, DISPLAY[st], st)}`;
}
const state = {};
for (const c of CONDITIONS) {
  try { state[c.tag] = JSON.parse(fs.readFileSync(`/home/z/my-project/data/${c.file}`, 'utf-8')); }
  catch { state[c.tag] = {}; }
}
const nb = Math.ceil(articles.length / BATCH);
let ran = 0;
for (let b = 0; b < nb; b++) {
  const batch = articles.slice(b * BATCH, (b + 1) * BATCH);
  if (batch.length === 0) break;
  const order = CONDITIONS.map((_, i) => CONDITIONS[(i + b) % CONDITIONS.length]);
  for (let pos = 0; pos < order.length; pos++) {
    const cond = order[pos];
    if (!batch.some(a => !state[cond.tag][a.url])) continue;
    const lines = batch.map(a => `id=${a.idx}: ${texts[cond.tag][a.url]}`);
    const userMsg = (cond.framed === 'anon'
      ? 'Headlines (each refers to a single unnamed company):\n\n'
      : 'Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n') + lines.join('\n');
    const params = { messages: [{ role: 'assistant', content: SYSTEM_PROMPT }, { role: 'user', content: userMsg }],
                    thinking: { type: 'disabled' } };
    if (cond.decoding === 'temp0') params.temperature = 0;
    let res = null;
    for (let attempt = 1; attempt <= CALL_BACKOFF_MS.length; attempt++) {
      try {
        const completion = await zai.chat.completions.create(params);
        res = { parsed: parseScoreResponse(completion.choices[0]?.message?.content || '', batch),
                model: completion.model || completion.id || '' };
        break;
      } catch (e) {
        const isRate = String(e).includes('429') || String(e).includes('Too many');
        logline(`attempt FAIL ${cond.tag} b=${b} try=${attempt} ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 70)}`);
        if (isRate && attempt >= 3) break;
        await new Promise(r => setTimeout(r, isRate ? CALL_BACKOFF_MS[attempt - 1] : 4000));
      }
    }
    if (res) {
      Object.assign(state[cond.tag], res.parsed);
      fs.writeFileSync(`/home/z/my-project/data/${cond.file}`, JSON.stringify(state[cond.tag], null, 1));
      logline(`attempt batch=${b} cond=${cond.tag} ok n=${Object.keys(res.parsed).length} model=${res.model}`);
      ran++;
    } else {
      logline(`attempt batch=${b} cond=${cond.tag} SKIPPED`);
    }
    await new Promise(r => setTimeout(r, 6000));
  }
}
const leftN = CONDITIONS.reduce((s, c) => s + (341 - Object.keys(state[c.tag]).length), 0);
logline(`ATTEMPT done: calls_ran=${ran} items_left=${leftN}`);
console.log(`ATTEMPT done: ran=${ran}, left=${leftN}`);
if (leftN === 0) { logline('SESSION5 ALL DONE (attempt runner)'); console.log('SESSION5 ALL DONE'); }
