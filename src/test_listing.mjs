const fs = await import('fs');
const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
const urls = [
  "https://www.marketwatch.com/investing/stock/aapl",
  "https://finance.yahoo.com/quote/AAPL/news/",
];
for (const u of urls) {
  try {
    const r = await zai.functions.invoke('page_reader', { url: u });
    const data = r.data || r;
    const text = (data.html || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
    console.log('=== ' + u + ' ===');
    console.log('title:', data.title);
    console.log('len:', text.length);
    console.log('text sample:', text.slice(0, 1200));
  } catch (e) {
    console.log('FAIL', u, String(e).slice(0, 120));
  }
}
