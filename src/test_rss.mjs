const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();
try {
  const r = await zai.functions.invoke('page_reader', { url: "https://feeds.finance.yahoo.com/rss/2.0/headline?s=MSFT&region=US&lang=en-US" });
  const data = r.data || r;
  const text = (data.html || data.text || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
  console.log('SERVER-SIDE RSS len:', text.length);
  console.log(text.slice(0, 1000));
} catch (e) {
  console.log('FAIL:', String(e).slice(0, 150));
}
