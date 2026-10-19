// Dry-run: verify session-5 text transformations without any API call.
import fs from 'fs';
import { DISPLAY, replaceFocal, anonymizeV2, verifyNoFocal, buildSwapMap } from './s5_transforms.mjs';

const articles = JSON.parse(fs.readFileSync('/home/z/my-project/data/news_scored.json', 'utf-8'))
  .map((a, i) => ({ ...a, idx: i }))
  .filter(a => a.date_iso && '2026-07-01' <= a.date_iso && a.date_iso <= '2026-10-14');

const swap = buildSwapMap();
console.log('swap map sample:', Object.entries(swap).slice(0, 6));
console.log('self-mappings (must be 0):', Object.entries(swap).filter(([k, v]) => k === v).length);

let anonBad = 0, swapBad = 0, changed = 0;
for (const a of articles) {
  const anon = anonymizeV2(a.title, a.ticker);
  if (anon !== a.title) changed++;
  if (verifyNoFocal(anon, a.ticker).length) { anonBad++; if (anonBad <= 3) console.log('ANON RESIDUAL:', a.ticker, '|', anon.slice(0, 90), verifyNoFocal(anon, a.ticker)); }
  const st = swap[a.ticker];
  const sText = replaceFocal(a.title, a.ticker, DISPLAY[st], st);
  if (verifyNoFocal(sText, a.ticker).length) { swapBad++; if (swapBad <= 3) console.log('SWAP RESIDUAL:', a.ticker, '->', st, '|', sText.slice(0, 90), verifyNoFocal(sText, a.ticker)); }
}
console.log(`anonymized v2: ${changed}/341 altered | anon residuals: ${anonBad}/341 | swap residuals: ${swapBad}/341`);

for (const want of ['AAPL', 'V', 'GE']) {
  const a = articles.find(x => x.ticker === want);
  const st = swap[a.ticker];
  console.log('\n---', want, '->', st, '---');
  console.log('N5 :', (`[${DISPLAY[a.ticker]}] ${a.title}`).slice(0, 110));
  console.log('A5 :', anonymizeV2(a.title, a.ticker).slice(0, 110));
  console.log('P5 :', ('[Company X] ' + anonymizeV2(a.title, a.ticker)).slice(0, 110));
  console.log('S5 :', (`[${DISPLAY[st]}] ${replaceFocal(a.title, a.ticker, DISPLAY[st], st)}`).slice(0, 110));
}
