// SESSION 6b: batch-size dose-response (pre-registered: audits/P3_preregistration_session6.md).
// Seeded sample of 50 in-window headlines (seed 20261025), named protocol text,
// ONE sitting, pass order B1a (25 singletons) -> B25 (2 batches of 25) -> B5 (10
// batches of 5) -> B1b (25 singletons), so the size-1 level is centered in
// session time. Resume-safe per-pass files. Log: scripts/llm_score_v6b.log
import fs from 'fs';
import { SYSTEM_PROMPT, DISPLAY } from './s5_transforms.mjs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v6b.log';
const SEED = 20261025;
const N = 50;

function logline(s) { fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`); }

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

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

async function callBatch(zai, batch, passTag, texts, size) {
  const lines = batch.map(a => `id=${a.idx}: ${texts[a.url]}`);
  const userMsg = 'Company context: each headline is prefixed with the company it refers to.\n\nHeadlines:\n' + lines.join('\n');
  const params = {
    messages: [
      { role: 'assistant', content: SYSTEM_PROMPT },
      { role: 'user', content: userMsg },
    ],
    thinking: { type: 'disabled' },
  };
  for (let attempt = 1; attempt <= 7; attempt++) {
    try {
      const completion = await zai.chat.completions.create(params);
      const parsed = parseScoreResponse(completion.choices[0]?.message?.content || '', batch);
      return { parsed, model: completion.model || completion.id || '' };
    } catch (e) {
      const isRate = String(e).includes('429') || String(e).includes('Too many');
      logline(`call FAIL ${passTag} size=${size} n=${batch.length} attempt=${attempt} ${isRate ? 'RATE' : 'PARSE'}: ${String(e).slice(0, 80)}`);
      await new Promise(r => setTimeout(r, isRate ? [30000, 60000, 90000, 150000, 240000, 360000][Math.min(attempt - 1, 5)] : 4000));
    }
  }
  return null;
}

async function runPass(zai, pass, articles, texts) {
  const stateFile = `/home/z/my-project/data/${pass.file}`;
  let state = {};
  try { state = JSON.parse(fs.readFileSync(stateFile, 'utf-8')); } catch {}
  const nb = Math.ceil(articles.length / pass.size);
  let doneCalls = 0;
  for (let b = 0; b < nb; b++) {
    const batch = articles.slice(b * pass.size, (b + 1) * pass.size);
    if (batch.length === 0) break;
    const need = batch.some(a => !state[a.url]);
    if (!need) { doneCalls++; continue; }
    const res = await callBatch(zai, batch, pass.tag, texts, pass.size);
    if (res) {
      Object.assign(state, res.parsed);
      fs.writeFileSync(stateFile, JSON.stringify(state, null, 1));
      logline(`pass=${pass.tag} batch=${b} size=${pass.size} ok n=${Object.keys(res.parsed).length} model=${res.model}`);
    } else {
      logline(`pass=${pass.tag} batch=${b} size=${pass.size} SKIPPED after attempts`);
    }
    await new Promise(r => setTimeout(r, 7000));
    doneCalls++;
  }
  console.log(`${pass.tag} done | n=${Object.keys(state).length}/${articles.length}`);
  logline(`pass=${pass.tag} COMPLETE n=${Object.keys(state).length}`);
}

async function main() {
  const zai = await ZAI.create();
  logline(`SESSION6B START seed=${SEED} n=${N} named-protocol thinking=disabled`);

  const inwin = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
  // seeded sample of 50, preserving corpus order inside the sample
  const rnd = mulberry32(SEED);
  const pool = inwin.slice();
  const picked = [];
  while (picked.length < N && pool.length) {
    picked.push(pool.splice(Math.floor(rnd() * pool.length), 1)[0]);
  }
  picked.sort((a, b) => a.idx - b.idx);
  fs.writeFileSync('/home/z/my-project/data/s6b_sample.json', JSON.stringify(picked.map(a => a.url), null, 1));
  logline(`sample archived n=${picked.length}`);

  const texts = {};
  for (const a of picked) texts[a.url] = `[${DISPLAY[a.ticker]}] ${a.title}`;
  // local re-index 0..49 for the id= fields
  const arts = picked.map((a, j) => ({ ...a, idx: j }));

  const first = arts.slice(0, 25);
  const second = arts.slice(25);
  await runPass(zai, { tag: 'B1a', file: 'llm_scores_s6b_b1a.json', size: 1 }, first, texts);
  await runPass(zai, { tag: 'B25', file: 'llm_scores_s6b_b25.json', size: 25 }, arts, texts);
  await runPass(zai, { tag: 'B5', file: 'llm_scores_s6b_b5.json', size: 5 }, arts, texts);
  await runPass(zai, { tag: 'B1b', file: 'llm_scores_s6b_b1b.json', size: 1 }, second, texts);
  logline('SESSION6B ALL DONE');
  console.log('SESSION6B ALL DONE');
}

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
