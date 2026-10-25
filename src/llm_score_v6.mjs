// SESSION 6: fictional-name control (pre-registered: audits/P3_preregistration_session6.md).
//
// Three passes over the SAME 341 in-window headlines, ONE sitting, batch size 25,
// three-way rotated call order per batch (b mod 3), protocol identical to v1-v5,
// thinking disabled, default decoding, per-call logging with served-model ID:
//   N6  named anchor                -> llm_scores_s6_named.json
//   A6  anonymized v2 + verification -> llm_scores_s6_anonv2.json
//   F6  fictional name (s6_fictional_map.json) -> llm_scores_s6_fictional.json
//
// Verification (pre-collection, forced): word-boundary check (session-5 rule)
// PLUS substring check on original aliases of length>=4 (the tier the 2026-10-25
// leakage audit added after "ExxonMobil"-class concatenated-variant gaps).
// Resume-safe: per-condition files checkpoint after every batch.
import fs from 'fs';
import { SYSTEM_PROMPT, DISPLAY, TICKERS, replaceFocal, anonymizeV2, verifyNoFocal, ALIASES } from './s5_transforms.mjs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const SCORED = '/home/z/my-project/data/news_scored.json';
const LOG = '/home/z/my-project/scripts/llm_score_v6.log';
const FMAP = JSON.parse(fs.readFileSync('/home/z/my-project/scripts/s6_fictional_map.json', 'utf-8'));
const BATCH = 25;

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
  { tag: 'N6', file: 'llm_scores_s6_named.json', framed: 'named' },
  { tag: 'A6', file: 'llm_scores_s6_anonv2.json', framed: 'anon' },
  { tag: 'F6', file: 'llm_scores_s6_fictional.json', framed: 'named' },
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

function substringLeaks(text, ticker) {
  const low = text.toLowerCase();
  const hits = [];
  for (const al of ALIASES[ticker] || []) {
    if (al.length >= 4 && low.includes(al.toLowerCase())) hits.push(al);
  }
  return hits;
}

// Concatenated name variants ("ExxonMobil", "JPMorganChase") evade the
// word-boundary replacement in s5_transforms.mjs (\bExxon\b does not match
// inside "ExxonMobil"). Session-6 transform: replace the no-space form of
// every multi-word alias with the fictional name, case-insensitively.
function replaceConcatVariants(title, ticker, replacementName) {
  let t = title;
  for (const al of ALIASES[ticker] || []) {
    if (!al.includes(' ')) continue;
    const joined = al.replace(/\s+/g, '');
    t = t.replace(new RegExp(jgedEscape(joined), 'gi'), replacementName);
  }
  return t;
}
function jgedEscape(s) { return s.replace(/[.*+?^${}()|[\]\\&]/g, '\\$&'); }

async function main() {
  const zai = await ZAI.create();
  logline(`SESSION6 START fictional_map=archived protocol=identical-v1v5 thinking=disabled`);

  const articles = JSON.parse(fs.readFileSync(SCORED, 'utf-8'))
    .map((a, i) => ({ ...a, idx: i }))
    .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');
  logline(`s6 in_window=${articles.length}`);

  const texts = { N6: {}, A6: {}, F6: {} };
  const verifyReport = { anon_residual: [], fic_residual_wordbound: [], fic_residual_substring: [], n_checked: 0, fic_name_missing: [] };
  for (const a of articles) {
    texts.N6[a.url] = `[${DISPLAY[a.ticker]}] ${a.title}`;
    const anon = anonymizeV2(a.title, a.ticker);
    texts.A6[a.url] = anon;
    const f = FMAP[a.ticker];
    let ficTitle = replaceFocal(a.title, a.ticker, f.name, f.ticker);
    ficTitle = replaceConcatVariants(ficTitle, a.ticker, f.name);
    texts.F6[a.url] = `[${f.name}] ${ficTitle}`;
    verifyReport.n_checked += 1;
    const bare = texts.F6[a.url].replace(/^\[[^\]]+\]\s*/, '');
    const rA = verifyNoFocal(anon, a.ticker);
    if (rA.length) verifyReport.anon_residual.push({ url: a.url, ticker: a.ticker, hits: rA });
    const rF = verifyNoFocal(bare, a.ticker);
    if (rF.length) verifyReport.fic_residual_wordbound.push({ url: a.url, ticker: a.ticker, hits: rF });
    const rS = substringLeaks(bare, a.ticker);
    if (rS.length) verifyReport.fic_residual_substring.push({ url: a.url, ticker: a.ticker, hits: rS });
    if (!texts.F6[a.url].includes(f.name)) verifyReport.fic_name_missing.push(a.url);
  }
  fs.writeFileSync('/home/z/my-project/data/s6_verify_report.json', JSON.stringify(verifyReport, null, 1));
  logline(`verify: anon_residual=${verifyReport.anon_residual.length} fic_wordbound=${verifyReport.fic_residual_wordbound.length} fic_substring=${verifyReport.fic_residual_substring.length} fic_name_missing=${verifyReport.fic_name_missing.length} of ${verifyReport.n_checked}`);
  if (verifyReport.fic_residual_substring.length > 0) {
    logline(`VERIFY BLOCK: ${verifyReport.fic_residual_substring.length} F6 texts leak original identity by substring; aborting before any call.`);
    console.log(`VERIFY BLOCK: ${verifyReport.fic_residual_substring.length} F6 texts leak original identity by substring; fix s6_fictional_map/s5_transforms first.`);
    process.exit(2);
  }

  const state = {};
  for (const c of CONDITIONS) {
    try { state[c.tag] = JSON.parse(fs.readFileSync(`/home/z/my-project/data/${c.file}`, 'utf-8')); }
    catch { state[c.tag] = {}; }
  }

  const nb = Math.ceil(articles.length / BATCH);
  for (let b = 0; b < nb; b++) {
    const batch = articles.slice(b * BATCH, (b + 1) * BATCH);
    if (batch.length === 0) break;
    const order = CONDITIONS.map((_, i) => CONDITIONS[(i + b) % CONDITIONS.length]);
    for (let pos = 0; pos < order.length; pos++) {
      const cond = order[pos];
      const need = batch.some(a => !state[cond.tag][a.url]);
      if (!need) continue;
      const res = await callBatch(zai, batch, cond, texts[cond.tag]);
      if (res) {
        Object.assign(state[cond.tag], res.parsed);
        fs.writeFileSync(`/home/z/my-project/data/${c_file(cond)}`, JSON.stringify(state[cond.tag], null, 1));
        logline(`batch=${b} cond=${cond.tag} pos=${pos} ok n=${Object.keys(res.parsed).length} model=${res.model}`);
      } else {
        logline(`batch=${b} cond=${cond.tag} pos=${pos} SKIPPED after attempts`);
      }
      await new Promise(r => setTimeout(r, 6000));
    }
    const done = CONDITIONS.map(c => `${c.tag}=${Object.keys(state[c.tag]).length}`).join(' ');
    console.log(`batch ${b + 1}/${nb} done | ${done}`);
    logline(`batch=${b} COMPLETE ${done}`);
  }
  logline('SESSION6 ALL DONE');
  console.log('SESSION6 ALL DONE');
}

function c_file(cond) { return cond.file; }

main().catch(e => { console.error('FATAL', String(e).slice(0, 300)); process.exit(1); });
