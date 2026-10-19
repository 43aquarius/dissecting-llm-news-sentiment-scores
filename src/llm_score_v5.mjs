// SESSION 5 controls (pre-registered: audits/P2_preregistration_session5.md).
//
// Six passes over the SAME 341 in-window headlines, ONE sitting, batch size 25,
// six-way rotated call order per batch (uniform time-of-session exposure):
//   N5  named, default decoding                       (anchor; draw-stability datapoint)
//   A5  anonymized v2, default decoding               (corrected alias table incl. "Visa";
//                                                      sentence-start capitalization; forced verification)
//   S5  identity swap, default decoding               (seeded derangement, seed 20261019)
//   P5  neutral prefix "[Company X]", default decoding (same text as A5)
//   T0a named, temperature 0
//   T0b named, temperature 0 (second round)
//
// Resume-safe: per-condition JSON files checkpoint after every batch; re-running
// skips completed URLs. Log: scripts/llm_score_v5.log (ISO ts, condition, batch,
// order position, model, temperature, n parsed).
// Transformations live in scripts/s5_transforms.mjs (shared with the dry-run).
import fs from 'fs';
import { SYSTEM_PROMPT, DISPLAY, TICKERS, replaceFocal, anonymizeV2, verifyNoFocal, buildSwapMap } from './s5_transforms.mjs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v5.log';
const BATCH = 25;
const SEED = 20261019;

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

const BACKOFF_MS = [30000, 60000, 90000, 120000, 180000, 300000];

async function callBatch(zai, batch, cond, texts) {
  const lines = batch.map(a => `id=${a.idx}: ${texts[a.url]}`);
  const userMsg = (cond.framed === 'anon'
    ? 'Headlines (each refers to a single unnamed company):\n\n'
    : 'Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n')
    + lines.join('\n');
  const params = {
    messages: [
      { role: 'assistant', content: SYSTEM_PROMPT },
      { role: 'user', content: userMsg },
    ],
    thinking: { type: 'disabled' },
  };
  if (cond.decoding === 'temp0') params.temperature = 0;
  for (let attempt = 1; attempt <= BACKOFF_MS.length; attempt++) {
    try {
      const completion = await zai.chat.completions.create(params);
      const parsed = parseScoreResponse(completion.choices[0]?.message?.content || '', batch);
      return { parsed, model: completion.model || completion.id || '' };
    } catch (e) {
      const isRate = String(e).includes('429') || String(e).includes('Too many');
      logline(`call FAIL ${cond.tag} n=${batch.length} attempt=${attempt} ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
      await new Promise(r => setTimeout(r, isRate ? BACKOFF_MS[attempt - 1] : 4000));
    }
  }
  return null;
}

async function main() {
  const zai = await ZAI.create();
  const swap = buildSwapMap();
  logline(`SESSION5 START seed=${SEED} swap_map=archived protocol=identical-v1v4 thinking=disabled`);

  const articles = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
  logline(`s5 in_window=${articles.length}`);

  // build per-condition texts + run forced verification for A5/P5/S5
  const texts = { N5: {}, A5: {}, S5: {}, P5: {}, T0a: {}, T0b: {} };
  const verifyReport = { anon_residual: [], swap_residual: [], n_checked: 0 };
  for (const a of articles) {
    texts.N5[a.url] = `[${DISPLAY[a.ticker]}] ${a.title}`;
    texts.T0a[a.url] = texts.N5[a.url];
    texts.T0b[a.url] = texts.N5[a.url];
    const anon = anonymizeV2(a.title, a.ticker);
    texts.A5[a.url] = anon;
    texts.P5[a.url] = `[Company X] ${anon}`;
    const st = swap[a.ticker];
    texts.S5[a.url] = `[${DISPLAY[st]}] ${replaceFocal(a.title, a.ticker, DISPLAY[st], st)}`;
    verifyReport.n_checked += 1;
    const rA = verifyNoFocal(anon, a.ticker);
    if (rA.length) verifyReport.anon_residual.push({ url: a.url, ticker: a.ticker, hits: rA });
    const rS = verifyNoFocal(texts.S5[a.url].replace(/^\[[^\]]+\]\s*/, ''), a.ticker);
    if (rS.length) verifyReport.swap_residual.push({ url: a.url, ticker: a.ticker, hits: rS });
  }
  fs.writeFileSync('/home/z/my-project/data/s5_verify_report.json', JSON.stringify(verifyReport, null, 1));
  logline(`verify: anon_residual=${verifyReport.anon_residual.length} swap_residual=${verifyReport.swap_residual.length} of ${verifyReport.n_checked}`);

  // load per-condition progress
  const state = {};
  for (const c of CONDITIONS) {
    try { state[c.tag] = JSON.parse(fs.readFileSync(`/home/z/my-project/data/${c.file}`, 'utf-8')); }
    catch { state[c.tag] = {}; }
  }

  const nb = Math.ceil(articles.length / BATCH);
  for (let b = 0; b < nb; b++) {
    const batch = articles.slice(b * BATCH, (b + 1) * BATCH);
    if (batch.length === 0) break;
    // six-way rotation: order rotated left by (b mod 6)
    const order = CONDITIONS.map((_, i) => CONDITIONS[(i + b) % CONDITIONS.length]);
    for (let pos = 0; pos < order.length; pos++) {
      const cond = order[pos];
      const need = batch.some(a => !state[cond.tag][a.url]);
      if (!need) continue;
      const res = await callBatch(zai, batch, cond, texts[cond.tag]);
      if (res) {
        Object.assign(state[cond.tag], res.parsed);
        fs.writeFileSync(`/home/z/my-project/data/${cond.file}`, JSON.stringify(state[cond.tag], null, 1));
        logline(`batch=${b} cond=${cond.tag} pos=${pos} ok n=${Object.keys(res.parsed).length} model=${res.model} temp=${cond.decoding}`);
      } else {
        logline(`batch=${b} cond=${cond.tag} pos=${pos} SKIPPED after attempts`);
      }
      await new Promise(r => setTimeout(r, 6000)); // throttle between calls (rate-limit friendly)
    }
    const done = CONDITIONS.map(c => `${c.tag}=${Object.keys(state[c.tag]).length}`).join(' ');
    console.log(`batch ${b + 1}/${nb} done | ${done}`);
    logline(`batch=${b} COMPLETE ${done}`);
  }
  logline('SESSION5 ALL DONE');
  console.log('SESSION5 ALL DONE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
