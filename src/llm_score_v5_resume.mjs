// SESSION 5 RESUME RUNNER (enhanced backoff per external review guidance).
// Completes the remaining ~21 batch calls of the pre-registered session 5
// (audits/P2_preregistration_session5.md) after a sustained 429 quota block.
//
// Strategy (patient, quota-aware, staggered):
//   PHASE 1  probe: one tiny chat call every 5 min (escalating to 10 min);
//            gives up after MAX_RUNTIME (default 4h) and exits with a clear code.
//   PHASE 2  run: once quota opens, process remaining batches in the SAME
//            six-way rotated order as the original protocol (time-of-session
//            balance preserved), 6s throttle between calls, per-call
//            exponential backoff [30s,60s,120s,240s,480s,600s], skip-and-requeue
//            on exhaustion, then re-enter PHASE 1 for stragglers (max 3 cycles).
// Resume-safe: identical per-condition JSON checkpoints; completed URLs skipped.
// Log: scripts/llm_score_v5.log (same as original) + console.
import fs from 'fs';
import { SYSTEM_PROMPT, DISPLAY, TICKERS, replaceFocal, anonymizeV2, verifyNoFocal, buildSwapMap } from './s5_transforms.mjs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v5.log';
const BATCH = 25;
const SEED = 20261019;
const MAX_RUNTIME_MS = parseInt(process.env.S5_MAX_RUNTIME_MS || '14400000', 10); // 4h default
const PROBE_START_MS = 300000, PROBE_MAX_MS = 600000;
const CALL_BACKOFF_MS = [30000, 60000, 120000, 240000, 480000, 600000];
const T0 = Date.now();

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

async function probeQuota(zai) {
  try {
    await zai.chat.completions.create({
      messages: [
        { role: 'assistant', content: 'Reply with a JSON array only.' },
        { role: 'user', content: 'id=0: probe\n\nReturn [{"id":0,"sentiment":0,"relevance":0}].' },
      ],
      thinking: { type: 'disabled' },
    });
    return true;
  } catch (e) {
    return String(e).includes('429') ? false : false; // any failure => not open
  }
}

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
  for (let attempt = 1; attempt <= CALL_BACKOFF_MS.length; attempt++) {
    try {
      const completion = await zai.chat.completions.create(params);
      const parsed = parseScoreResponse(completion.choices[0]?.message?.content || '', batch);
      return { parsed, model: completion.model || completion.id || '' };
    } catch (e) {
      const isRate = String(e).includes('429') || String(e).includes('Too many');
      logline(`call FAIL ${cond.tag} n=${batch.length} attempt=${attempt} ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
      // quota can re-close mid-run: stop wasting attempts on hard 429 after 2 tries
      if (isRate && attempt >= 3) return null;
      await new Promise(r => setTimeout(r, isRate ? CALL_BACKOFF_MS[attempt - 1] : 4000));
    }
  }
  return null;
}

async function main() {
  const zai = await ZAI.create();
  const swap = buildSwapMap();
  logline(`SESSION5 RESUME START seed=${SEED} protocol=identical max_runtime_h=${(MAX_RUNTIME_MS / 3600000).toFixed(1)}`);

  const articles = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');

  // per-condition texts (identical to original runner)
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

  // load checkpoints
  const state = {};
  for (const c of CONDITIONS) {
    try { state[c.tag] = JSON.parse(fs.readFileSync(`/home/z/my-project/data/${c.file}`, 'utf-8')); }
    catch { state[c.tag] = {}; }
  }
  const remaining0 = CONDITIONS.map(c => `${c.tag}=${341 - Object.keys(state[c.tag]).length}`).join(' ');
  logline(`resume remaining: ${remaining0}`);

  const nb = Math.ceil(articles.length / BATCH);
  let cycle = 0;
  while (cycle < 3) {
    cycle++;
    // PHASE 1: patient probing until quota opens or runtime budget exhausted
    let probeWait = PROBE_START_MS, probeN = 0, open = false;
    while (Date.now() - T0 < MAX_RUNTIME_MS) {
      probeN++;
      if (await probeQuota(zai)) { logline(`probe #${probeN} OPEN`); open = true; break; }
      const elapsed = ((Date.now() - T0) / 60000).toFixed(1);
      logline(`probe #${probeN} blocked (elapsed ${elapsed} min), waiting ${probeWait / 1000}s`);
      await new Promise(r => setTimeout(r, probeWait));
      probeWait = Math.min(probeWait * 1.5, PROBE_MAX_MS);
    }
    if (!open) {
      logline('RESUME GIVE-UP: quota still blocked at runtime budget; rerun this script later — checkpoints intact.');
      console.log('RESUME GIVE-UP');
      return;
    }

    // PHASE 2: run remaining batches in original rotation order
    let skipped = 0;
    for (let b = 0; b < nb; b++) {
      const batch = articles.slice(b * BATCH, (b + 1) * BATCH);
      if (batch.length === 0) break;
      const order = CONDITIONS.map((_, i) => CONDITIONS[(i + b) % CONDITIONS.length]);
      for (let pos = 0; pos < order.length; pos++) {
        const cond = order[pos];
        const need = batch.some(a => !state[cond.tag][a.url]);
        if (!need) continue;
        if (Date.now() - T0 > MAX_RUNTIME_MS) { logline('runtime budget hit mid-run; exiting loop'); skipped++; continue; }
        const res = await callBatch(zai, batch, cond, texts[cond.tag]);
        if (res) {
          Object.assign(state[cond.tag], res.parsed);
          fs.writeFileSync(`/home/z/my-project/data/${cond.file}`, JSON.stringify(state[cond.tag], null, 1));
          logline(`batch=${b} cond=${cond.tag} pos=${pos} ok n=${Object.keys(res.parsed).length} model=${res.model} temp=${cond.decoding} cycle=${cycle}`);
        } else {
          logline(`batch=${b} cond=${cond.tag} pos=${pos} SKIPPED cycle=${cycle}`);
          skipped++;
        }
        await new Promise(r => setTimeout(r, 6000)); // stagger between calls
      }
      const done = CONDITIONS.map(c => `${c.tag}=${Object.keys(state[c.tag]).length}`).join(' ');
      logline(`batch=${b} CYCLE${cycle} PASS ${done}`);
    }

    const leftN = CONDITIONS.reduce((s, c) => s + (341 - Object.keys(state[c.tag]).length), 0);
    logline(`cycle=${cycle} complete: ${leftN} items still missing, skipped_calls=${skipped}`);
    if (leftN === 0) { logline('SESSION5 ALL DONE (resume)'); console.log('SESSION5 ALL DONE'); return; }
    if (skipped === 0) {
      logline('no progress possible (quota open but calls failing); giving up to avoid hammering.');
      console.log('RESUME STALLED'); return;
    }
  }
  logline('RESUME EXIT after 3 cycles with items missing');
  console.log('RESUME INCOMPLETE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
