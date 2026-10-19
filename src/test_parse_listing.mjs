import fs from 'fs';
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
const r = await zai.functions.invoke('page_reader', { url: "https://www.marketwatch.com/investing/stock/aapl" });
const data = r.data || r;
fs.writeFileSync('/home/z/my-project/data/mw_aapl.html', data.html || '');
console.log('saved', (data.html || '').length, 'bytes');
