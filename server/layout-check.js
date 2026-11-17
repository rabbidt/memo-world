// npm run layout: read the island layout spreadsheet, say what it contains and what looks wrong,
// and save a top-down map (world/island-map.svg) plus a plain copy (world/starting-layout.json).
import fs from 'node:fs';
import path from 'node:path';
import { loadLayout, expandLayout, mapSvg, LAYOUT_JSON } from './layout.js';

const { layout, warnings, source } = loadLayout({ file: process.argv[2], log: null });
const { zones, objects } = expandLayout(layout);
console.log(`Layout read from ${source}\n`);
console.log(`Places (${zones.length}):`);
for (const z of zones) console.log(`  ${z.name.padEnd(18)} x ${String(z.x).padStart(4)}  z ${String(z.z).padStart(4)}  size ${z.radius}`);
const counts = {};
for (const o of objects) counts[o.kind] = (counts[o.kind] || 0) + 1;
console.log(`\nThings (${objects.length}): ${Object.entries(counts).map(([k, n]) => `${k} ×${n}`).join(', ')}`);
console.log(warnings.length ? `\nWorth a look:\n${warnings.map((w) => `  - ${w}`).join('\n')}` : '\nNo problems found.');
const dir = path.dirname(LAYOUT_JSON);
fs.writeFileSync(path.join(dir, 'island-map.svg'), mapSvg(layout));
fs.writeFileSync(LAYOUT_JSON, `${JSON.stringify(layout, null, 1)}\n`);
console.log(`\nSaved the map to ${path.join(dir, 'island-map.svg')} (open it in a browser).`);
console.log('The island picks the layout up the next time the server starts. Things Ash made himself are kept.');
