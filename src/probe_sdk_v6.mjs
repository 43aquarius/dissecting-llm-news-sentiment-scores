// Probe SDK capabilities: temperature param, model param, list of usable models.
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
const LOG = '/home/z/my-project/scripts/probe_v6.log';
function log(s) { fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`); console.log(s); }
fs.writeFileSync(LOG, '');

// 1. Baseline default call: what model is served?
try {
  const c = await zai.chat.completions.create({
    messages: [{ role: 'user', content: 'Reply with exactly: OK' }],
    thinking: { type: 'disabled' },
  });
  log(`default model served: ${c.model || c.id || '(unknown)'} | content=${(c.choices[0]?.message?.content || '').slice(0, 20)}`);
} catch (e) { log(`default call FAIL: ${String(e).slice(0, 150)}`); }

// 2. temperature=0 accepted?
try {
  const c1 = await zai.chat.completions.create({
    messages: [{ role: 'user', content: 'Give a one-word sentiment for: "Acme beats earnings expectations." Answer positive/negative/neutral.' }],
    thinking: { type: 'disabled' }, temperature: 0,
  });
  const c2 = await zai.chat.completions.create({
    messages: [{ role: 'user', content: 'Give a one-word sentiment for: "Acme beats earnings expectations." Answer positive/negative/neutral.' }],
    thinking: { type: 'disabled' }, temperature: 0,
  });
  const a = (c1.choices[0]?.message?.content || '').trim();
  const b = (c2.choices[0]?.message?.content || '').trim();
  log(`temperature=0 accepted: YES | model=${c1.model || c1.id} | run1="${a}" run2="${b}" identical=${a === b}`);
} catch (e) { log(`temperature=0 FAIL: ${String(e).slice(0, 150)}`); }

// 3. explicit model param — which models exist?
const candidates = ['glm-4-plus', 'glm-4-flash', 'glm-4-air', 'glm-4-long', 'glm-4.5', 'glm-4.6', 'glm-4.5-air', 'glm-4.5-flash', 'glm-zero-preview', 'glm-4.5v'];
for (const m of candidates) {
  try {
    const c = await zai.chat.completions.create({
      messages: [{ role: 'user', content: 'Reply with exactly: OK' }],
      thinking: { type: 'disabled' }, model: m,
    });
    log(`model "${m}": OK (served=${c.model || c.id || '?'}) content=${(c.choices[0]?.message?.content || '').slice(0, 15)}`);
  } catch (e) { log(`model "${m}": FAIL ${String(e).slice(0, 90)}`); }
  await new Promise(r => setTimeout(r, 1500));
}
log('PROBE DONE');
