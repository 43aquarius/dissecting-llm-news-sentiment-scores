// Model fingerprint probes (P3, external-validity threat documentation).
// Three independent pieces of evidence about which model the serving endpoint
// actually runs, archived to logs/model_fingerprint.log + data/model_fingerprint.json:
//   F1  self-identification probe (ask the model to name itself)
//   F2  response metadata (the `model` field the API returns per call)
//   F3  capability/knowledge probe (fixed 5-question battery; changes across
//       served models would change the fingerprint distribution)
// Rate-limit aware: single tiny probe first; exits quietly if 429 persists.
import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');

const LOG = '/home/z/my-project/logs/model_fingerprint.log';
const OUT = '/home/z/my-project/data/model_fingerprint.json';

function log(s) { fs.appendFileSync(LOG, `[${new Date().toISOString()}] ${s}\n`); }

async function one(zai, userMsg, opts = {}) {
  const completion = await zai.chat.completions.create({
    messages: [{ role: 'user', content: userMsg }],
    thinking: { type: 'disabled' },
    ...opts,
  });
  return {
    served_model: completion.model || completion.id || '(none)',
    content: String(completion.choices[0]?.message?.content || '').slice(0, 400),
  };
}

const zai = await ZAI.create();
log('FINGERPRINT PROBE START');
const R = { timestamp: new Date().toISOString(), probes: [] };

// gate on quota: one minimal probe
try {
  const gate = await one(zai, 'Reply with the single word: ok');
  log(`gate OPEN served_model=${gate.served_model}`);
  R.gate = 'open';
  R.gate_served_model = gate.served_model;

  // F1: self-identification
  try {
    const r = await one(zai, 'Which model are you? State your exact model name and version as reported by your system, in one short sentence.');
    R.probes.push({ type: 'F1_self_identification', served_model: r.served_model, answer: r.content });
    log(`F1 served_model=${r.served_model} answer=${r.content.slice(0, 120)}`);
  } catch (e) { log(`F1 FAIL ${String(e).slice(0, 80)}`); R.probes.push({ type: 'F1', error: String(e).slice(0, 80) }); }

  // F2: metadata under a DIFFERENT requested model string (the known-ignored parameter)
  try {
    const r = await one(zai, 'Reply with the single word: ok', { model: 'some-other-model-x' });
    R.probes.push({ type: 'F2_metadata_with_foreign_model_string', requested: 'some-other-model-x', served_model: r.served_model, content: r.content });
    log(`F2 requested=some-other-model-x served_model=${r.served_model}`);
  } catch (e) { log(`F2 FAIL ${String(e).slice(0, 80)}`); R.probes.push({ type: 'F2', error: String(e).slice(0, 80) }); }

  // F3: fixed knowledge battery (deterministic-ish, temperature 0)
  const Q = [
    'What is the capital of France? Answer with the city name only.',
    'Compute 17*23 and answer with the number only.',
    'Name the currency of Japan in one word.',
    'What year did the Berlin Wall fall? Answer with the year only.',
    'Is water H2O? Answer yes or no.',
  ];
  for (let i = 0; i < Q.length; i++) {
    try {
      const r = await one(zai, Q[i], { temperature: 0 });
      R.probes.push({ type: 'F3_battery', q: i, served_model: r.served_model, answer: r.content });
      log(`F3 q${i} served_model=${r.served_model} answer=${r.content.slice(0, 60)}`);
    } catch (e) { log(`F3 q${i} FAIL ${String(e).slice(0, 80)}`); R.probes.push({ type: 'F3', q: i, error: String(e).slice(0, 80) }); }
  }
  fs.writeFileSync(OUT, JSON.stringify(R, null, 1));
  log('FINGERPRINT PROBE DONE -> data/model_fingerprint.json');
  console.log('FINGERPRINT DONE');
} catch (e) {
  log(`gate BLOCKED: ${String(e).slice(0, 100)}`);
  console.log('FINGERPRINT BLOCKED (quota)');
  process.exit(0);
}
