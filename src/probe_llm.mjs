const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
try {
  const c = await zai.chat.completions.create({ messages: [{ role: 'user', content: 'Reply with exactly: OK' }], thinking: { type: 'disabled' } });
  console.log('LLM OK:', (c.choices[0]?.message?.content || '').slice(0, 30));
} catch (e) {
  console.log('LLM FAIL:', String(e).slice(0, 100));
}
