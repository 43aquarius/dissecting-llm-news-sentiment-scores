const { default: ZAI } = await import('/home/z/.bun/install/global/node_modules/z-ai-web-dev-sdk/dist/index.js');
const zai = await ZAI.create();

// Test 1: page_reader on GDELT API (server-side fetch, different IP)
const gdeltUrl = "https://api.gdeltproject.org/api/v2/doc/doc?query=(Apple%20OR%20AAPL)%20sourcelang%3Aenglish&mode=artlist&maxrecords=10&sort=hybridrel&format=json";
try {
  const r = await zai.functions.invoke('page_reader', { url: gdeltUrl });
  const data = r.data || r;
  const text = data.html || data.text || JSON.stringify(data);
  console.log('GDELT via page_reader OK, len:', text.length);
  console.log('head:', text.slice(0, 300));
} catch (e) {
  console.log('page_reader GDELT FAILED:', String(e).slice(0, 150));
}

// Test 2: web_search via SDK directly
try {
  const r2 = await zai.functions.invoke('web_search', { query: 'Microsoft MSFT stock news October 2026', num: 10 });
  console.log('\nweb_search OK, results:', (r2.data || r2).length || 'unknown');
  const arr = Array.isArray(r2) ? r2 : (r2.data || r2.results || []);
  for (const item of arr.slice(0, 5)) {
    console.log(`  ${item.date || '-'} | ${(item.name || '').slice(0, 60)}`);
  }
} catch (e) {
  console.log('web_search FAILED:', String(e).slice(0, 150));
}
