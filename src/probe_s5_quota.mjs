// 单条最小探测：判断会话5配额是否恢复
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
try {
  const c = await zai.chat.completions.create({
    messages: [
      { role: 'assistant', content: 'Return only a JSON array.' },
      { role: 'user', content: 'id=0: Apple beats earnings expectations\n\nReturn [{"id":0,"sentiment":X,"relevance":Y}] with X,Y integers.' },
    ],
    thinking: { type: 'disabled' },
  });
  console.log('PROBE OK model=', c.model || c.id || '', 'content=', String(c.choices[0]?.message?.content || '').slice(0, 60));
} catch (e) {
  console.log('PROBE FAIL:', String(e).slice(0, 120));
}
