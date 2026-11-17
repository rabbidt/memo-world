// Checks the island layout: the spreadsheet reads cleanly, matches the saved copy, and a changed
// layout relays the island without touching what Ash made. Run with: npm test
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'memo-layout-'));
const layoutFile = path.join(tmp, 'layout.json');
process.env.MEMO_DB = path.join(tmp, 'memo.db');
process.env.MEMO_LAYOUT = layoutFile; // not an .xlsx, so the world is seeded from this JSON

const { loadLayout, expandLayout, mapSvg, LAYOUT_XLSX, LAYOUT_JSON, LAND_RADIUS } = await import('../server/layout.js');
const shipped = path.join(path.dirname(LAYOUT_JSON), 'island-layout.xlsx');

// 1. The spreadsheet and the saved JSON copy say the same thing.
const fromSheet = loadLayout({ file: shipped, log: null });
const saved = JSON.parse(fs.readFileSync(LAYOUT_JSON, 'utf8'));
assert.deepEqual(JSON.parse(JSON.stringify(fromSheet.layout)), saved, 'run "npm run layout" after editing the spreadsheet');
assert.ok(fromSheet.warnings.every((w) => /waiting for models/.test(w)), fromSheet.warnings.join('\n'));

// 2. It has what Ash cannot do without, and everything stands on the land.
const world = expandLayout(saved);
for (const kind of ['notice_board', 'burrow', 'computer', 'library_tower']) assert.ok(world.objects.some((o) => o.kind === kind && o.zone_id), `${kind} is in the layout`);
for (const z of world.zones) assert.ok(Math.hypot(z.x, z.z) < LAND_RADIUS, `${z.name} is on the island`);
for (const o of world.objects) assert.ok(Math.hypot(o.x, o.z) < LAND_RADIUS + 4, `${o.kind} is on the island`);
assert.deepEqual(expandLayout(saved), world, 'the same layout always gives the same island');
assert.match(mapSvg(saved), /^<svg/);

// 3. Seeding, then changing the layout: places and starting things follow, Ash's own things stay.
fs.writeFileSync(layoutFile, JSON.stringify(saved));
const { seedWorld, getZones, getObjects, getMemo, addCreation, featureZone, getTerrain } = await import('../server/world.js');
seedWorld();
assert.equal(getZones().length, saved.places.length);
assert.equal(featureZone('notice_board'), 'board');
assert.equal(featureZone('burrow'), 'nook');
assert.equal(getMemo().zone, 'nook');
assert.ok(getTerrain().some((t) => t.lift > 3), 'the lookout hill is part of the terrain');
const before = getObjects().length;
seedWorld();
assert.equal(getObjects().length, before, 'starting again with the same layout changes nothing');

const made = addCreation('garden', { name: 'Pebble Stack', story: 'x', parts: [] });
const changed = structuredClone(saved);
changed.places = changed.places.filter((p) => p.id !== 'garden');
changed.things = changed.things.filter((t) => t.place !== 'garden' && t.kind !== 'notice_board');
changed.things.find((t) => t.kind === 'computer').place = 'nook';
changed.places.find((p) => p.id === 'pond').x = -12;
fs.writeFileSync(layoutFile, JSON.stringify(changed));
seedWorld();
assert.ok(!getZones().some((z) => z.id === 'garden'), 'the garden is gone');
assert.equal(getZones().find((z) => z.id === 'pond').x, -12, 'the pond moved');
assert.equal(getObjects().find((o) => o.kind === 'pond' && o.zone_id === 'pond').x, -12, 'and its water moved with it');
assert.equal(featureZone('notice_board'), null);
assert.equal(featureZone('computer'), 'nook', 'the computer now lives at the den');
const kept = getObjects().find((o) => o.id === made.id);
assert.ok(kept && kept.zone_id === 'nook', "Ash's creation survived and moved to a place that still exists");

console.log('Layout checks passed.');
