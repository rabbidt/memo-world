// The world is data: zones and objects live in SQLite, and the browser builds whatever it finds.
import { all, get, run, nowIso, getState, setState, emit } from './db.js';

const ZONES = [
  { id: 'board', name: 'Notice Board', x: 0, z: 0, radius: 4.5,
    description: 'A crooked wooden board at the crossing of the island paths. Ash pins wishes here, and gifts from the Keeper appear beside it.',
    gatherables: ['pin', 'paper scrap'] },
  { id: 'nook', name: 'Den', x: -9, z: 9, radius: 5,
    description: 'A snug den under a grassy mound with a round door. Home. The best place to nap.',
    gatherables: ['moss tuft', 'soft lint', 'shed fur'] },
  { id: 'garden', name: 'Garden', x: 11, z: 9, radius: 6.5,
    description: 'Little fenced plots of dark soil with sprouts, flowers and a watering can.',
    gatherables: ['seed', 'petal', 'pebble', 'sprig'] },
  { id: 'workshop', name: 'Workshop', x: 15, z: -8, radius: 6,
    description: 'An open-sided hut with a workbench, pegs of tools and a little chimney. Things get made here.',
    gatherables: ['wood scrap', 'twine', 'bent nail', 'clay lump'] },
  { id: 'library', name: 'Little Library', x: -2, z: -17, radius: 5.5,
    description: 'A tiny round tower of stone with shelves of weathered books, a warm lantern, and a little computer on a desk outside that can look things up in the wide world.',
    gatherables: ['pressed leaf', 'paper scrap', 'ribbon'] },
  { id: 'pond', name: 'Pond', x: -16, z: -6, radius: 7,
    description: 'Still green water ringed with reeds and lily pads. Dragonflies by day, fireflies at night.',
    gatherables: ['reed', 'smooth stone', 'lily petal', 'dew drop'] },
  { id: 'meadow', name: 'Meadow', x: 4, z: 21, radius: 6.5,
    description: 'Tall soft grass and clover that leans with the wind. Feathers drift down here sometimes.',
    gatherables: ['feather', 'clover', 'dandelion fluff', 'grass blade'] },
  { id: 'shore', name: 'Shore', x: -24, z: 17, radius: 6,
    description: 'A curve of pale sand where the sea leaves small treasures.',
    gatherables: ['shell', 'driftwood', 'sea glass', 'sand dollar'] },
  { id: 'lookout', name: 'Lookout Hill', x: 22, z: -21, radius: 5.5,
    description: 'The highest point of the island, with an old stump to sit on and the whole sea to look at.',
    gatherables: ['quartz chip', 'pine cone', 'lichen'] },
];

// Small seeded random so the island is the same every time it is created.
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

function addObject(o) {
  const r = run(`INSERT INTO objects(zone_id, kind, name, x, z, rot, scale, params, story, created_by, created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?)`,
    o.zone_id ?? null, o.kind, o.name ?? null, o.x, o.z, o.rot ?? 0, o.scale ?? 1,
    JSON.stringify(o.params ?? {}), o.story ?? null, o.created_by ?? 'world', nowIso());
  return Number(r.lastInsertRowid);
}

export function seedWorld() {
  if (get('SELECT COUNT(*) AS n FROM zones').n > 0) return;
  for (const z of ZONES) {
    run('INSERT INTO zones(id, name, description, x, z, radius, gatherables) VALUES(?,?,?,?,?,?,?)',
      z.id, z.name, z.description, z.x, z.z, z.radius, JSON.stringify(z.gatherables));
  }
  const Z = Object.fromEntries(ZONES.map((z) => [z.id, z]));
  const at = (id, dx, dz) => ({ zone_id: id, x: Z[id].x + dx, z: Z[id].z + dz });

  // Landmarks
  addObject({ ...at('board', 0, -1.2), kind: 'notice_board', name: 'Notice Board' });
  addObject({ ...at('board', 2.6, 0.6), kind: 'lantern' });
  addObject({ ...at('board', -2.4, 1.4), kind: 'signpost' });
  addObject({ ...at('nook', 0, -0.5), kind: 'burrow', name: 'Den', rot: 2.4 });
  addObject({ ...at('nook', 2.6, 1.8), kind: 'lantern' });
  addObject({ ...at('nook', -2.8, 1.5), kind: 'mushrooms' });
  for (const [dx, dz, crop] of [[-2.2, -1.6, 'sprout'], [2.2, -1.6, 'flower'], [-2.2, 2.0, 'leafy'], [2.2, 2.0, 'sprout']]) {
    addObject({ ...at('garden', dx, dz), kind: 'garden_plot', params: { crop } });
  }
  addObject({ ...at('garden', 0, 0.2), kind: 'watering_can', rot: 0.7 });
  addObject({ ...at('garden', 4.6, -3.2), kind: 'lantern' });
  addObject({ ...at('workshop', 0, -1), kind: 'workshop_hut', name: 'Workshop', rot: -0.5 });
  addObject({ ...at('workshop', -3.2, 2.2), kind: 'log_pile', rot: 0.4 });
  addObject({ ...at('library', 0, -0.8), kind: 'library_tower', name: 'Little Library', rot: 0.15 });
  addObject({ ...at('library', 3.0, 1.6), kind: 'bench', rot: -0.9 });
  addObject({ ...at('library', -3.0, 1.2), kind: 'computer', name: "Ash's Computer", rot: 0.9 });
  addObject({ ...at('pond', 0, 0), kind: 'pond', name: 'Pond', params: { radius: 4.6 } });
  addObject({ ...at('pond', 5.6, 1.5), kind: 'bench', rot: 1.4 });
  addObject({ ...at('lookout', 0.6, 0.4), kind: 'stump', name: 'Sitting Stump' });
  addObject({ ...at('lookout', -1.8, -1.2), kind: 'lantern' });
  addObject({ ...at('shore', 1.5, 0.5), kind: 'driftwood', rot: 0.8 });
  addObject({ ...at('shore', -1.2, -1.6), kind: 'shells' });
  addObject({ ...at('meadow', 0, 0), kind: 'flower_patch', params: { count: 26, spread: 5.5 } });

  // Low curving dry-stone walls that hug the places.
  for (const [id, radius, from, to] of [['garden', 6.2, -0.6, 2.9], ['library', 5.0, 2.0, 5.6], ['nook', 4.9, 2.6, 5.3], ['workshop', 5.6, -2.4, 0.4], ['board', 4.4, 3.5, 5.2], ['pond', 6.6, 3.6, 5.9], ['lookout', 4.6, -1.2, 1.6]]) {
    addObject({ zone_id: null, x: Z[id].x, z: Z[id].z, kind: 'wall', params: { radius, from, to } });
  }

  // Scattered scenery, kept clear of the zone centres.
  const rand = rng(20261117);
  const clear = (x, z, pad = 0.7) => ZONES.every((zn) => Math.hypot(x - zn.x, z - zn.z) > zn.radius * pad);
  const scatter = (kind, count, rMin, rMax, mk = () => ({})) => {
    let placed = 0, guard = 0;
    while (placed < count && guard++ < count * 40) {
      const a = rand() * Math.PI * 2, r = rMin + Math.sqrt(rand()) * (rMax - rMin);
      const x = Math.cos(a) * r, z = Math.sin(a) * r;
      if (!clear(x, z)) continue;
      addObject({ kind, x, z, rot: rand() * Math.PI * 2, scale: 0.75 + rand() * 0.6, params: mk() });
      placed++;
    }
  };
  // Trees grow in clumps, with singles in between.
  const clump = (kind, groups, size) => {
    for (let gI = 0, guard = 0; gI < groups && guard < 400; guard++) {
      const a = rand() * Math.PI * 2, r = 7 + Math.sqrt(rand()) * 22, cx = Math.cos(a) * r, cz = Math.sin(a) * r;
      if (!clear(cx, cz, 1.0)) continue;
      gI++;
      for (let i = 0; i < size; i++) {
        const x = cx + (rand() - 0.5) * 5.5, z = cz + (rand() - 0.5) * 5.5;
        if (clear(x, z, 0.85)) addObject({ kind, x, z, rot: rand() * Math.PI * 2, scale: 0.7 + rand() * 0.75, params: { hue: rand() } });
      }
    }
  };
  clump('tree', 13, 5); clump('pine', 6, 4);
  scatter('tree', 14, 5, 30, () => ({ hue: rand() }));
  scatter('pine', 6, 10, 31, () => ({ hue: rand() }));
  scatter('rock', 22, 4, 33, () => ({ seed: Math.floor(rand() * 1e6) }));
  scatter('bush', 44, 4, 31, () => ({ hue: rand(), berries: rand() > 0.6 }));
  scatter('flower_patch', 26, 4, 30, () => ({ count: 5 + Math.floor(rand() * 6), spread: 1.4 }));
  scatter('mushrooms', 7, 6, 28);

  setState('memo', {
    zone: 'nook', x: Z.nook.x + 3.2, z: Z.nook.z + 2.8, activity: 'idle', mood: 'curious',
    energy: 80, thoughtEnglish: 'Oh. A whole island. Where should I look first?', thought: 'Oh. A whole island. Where should I look first?', asleep: false, napUntil: null,
  });
  setState('born_at', nowIso());
}

export const getZones = () => all('SELECT * FROM zones').map((z) => ({ ...z, gatherables: JSON.parse(z.gatherables) }));
export const getZone = (id) => getZones().find((z) => z.id === id);
export const getObjects = () => all('SELECT * FROM objects ORDER BY id').map((o) => ({ ...o, params: JSON.parse(o.params) }));
export const getInventory = () => all('SELECT * FROM items WHERE qty > 0 ORDER BY name');
export const getMemo = () => getState('memo');

export function updateMemo(patch) {
  const memo = { ...getMemo(), ...patch };
  memo.energy = Math.max(0, Math.min(100, Math.round(memo.energy)));
  setState('memo', memo);
  emit('memo', { memo });
  return memo;
}

export function addItem(name, qty = 1, source = 'gathered', note = null) {
  run(`INSERT INTO items(name, qty, source, note, updated_at) VALUES(?,?,?,?,?)
    ON CONFLICT(name) DO UPDATE SET qty = qty + excluded.qty, updated_at = excluded.updated_at,
    note = COALESCE(excluded.note, note)`, name.toLowerCase().slice(0, 60), qty, source, note, nowIso());
  emit('inventory');
}
export function takeItem(name, qty = 1) {
  const row = get('SELECT qty FROM items WHERE name = ?', name.toLowerCase());
  if (!row || row.qty < qty) return false;
  run('UPDATE items SET qty = qty - ?, updated_at = ? WHERE name = ?', qty, nowIso(), name.toLowerCase());
  emit('inventory');
  return true;
}

// Find a free spot for a new creation: rings of slots around the zone centre, clear of other objects.
export function findSpot(zoneId, gap = 1.5) {
  const zone = getZone(zoneId);
  const others = all('SELECT x, z FROM objects WHERE zone_id = ? OR (ABS(x - ?) < 14 AND ABS(z - ?) < 14)', zoneId, zone.x, zone.z);
  for (let ring = 0; ring < 8; ring++) {
    const r = zone.radius * (gap > 2 ? 0.9 : 0.55) + ring * 1.1;
    const n = Math.floor((Math.PI * 2 * r) / (gap + 0.2));
    const offset = ring * 0.37 + others.length * 0.11;
    for (let i = 0; i < n; i++) {
      const a = offset + (i / n) * Math.PI * 2;
      const x = zone.x + Math.cos(a) * r, z = zone.z + Math.sin(a) * r;
      if (Math.hypot(x, z) < 33 && others.every((o) => Math.hypot(o.x - x, o.z - z) > gap)) return { x, z, rot: a + Math.PI };
    }
  }
  return { x: zone.x + (Math.random() - 0.5) * zone.radius, z: zone.z + (Math.random() - 0.5) * zone.radius, rot: 0 };
}

export function addSite(zoneId, name) {
  const spot = findSpot(zoneId, 3.4);
  const id = addObject({ zone_id: zoneId, kind: 'build_site', name: `Site: ${name}`, ...spot, created_by: 'memo' });
  const obj = { ...get('SELECT * FROM objects WHERE id = ?', id), params: {} };
  emit('object', { object: obj });
  return obj;
}
export function removeObject(id) {
  run('DELETE FROM objects WHERE id = ?', id);
  emit('object_removed', { id });
}
export function moveObject(id, zoneId) {
  const spot = findSpot(zoneId);
  run('UPDATE objects SET zone_id = ?, x = ?, z = ?, rot = ? WHERE id = ?', zoneId, spot.x, spot.z, spot.rot, id);
  const o = get('SELECT * FROM objects WHERE id = ?', id);
  emit('object_removed', { id });
  emit('object', { object: { ...o, params: JSON.parse(o.params) } });
}

export function addPet(zoneId, recipe) {
  const spot = findSpot(zoneId, 1.2);
  const id = addObject({ zone_id: zoneId, kind: 'pet', name: recipe.name, x: spot.x, z: spot.z,
    params: recipe, story: recipe.story, created_by: 'world' });
  const obj = { ...get('SELECT * FROM objects WHERE id = ?', id), params: recipe };
  emit('object', { object: obj });
  return obj;
}
// Pets are simple creatures with a mind of their own: mostly they tag along, sometimes they wander.
export function movePets(memoZone, placeInZone) {
  const zones = getZones();
  for (const pet of all("SELECT id, zone_id FROM objects WHERE kind = 'pet'")) {
    const roll = Math.random();
    const zone = roll < 0.55 ? memoZone : roll < 0.75 ? zones[Math.floor(Math.random() * zones.length)].id : pet.zone_id;
    const spot = placeInZone(zone);
    run('UPDATE objects SET zone_id = ?, x = ?, z = ? WHERE id = ?', zone, spot.x, spot.z, pet.id);
    emit('object_moved', { id: pet.id, zone_id: zone, x: spot.x, z: spot.z });
  }
}

export function addCreation(zoneId, recipe, at = null, createdBy = 'memo') {
  const spot = at || findSpot(zoneId);
  const id = addObject({ zone_id: zoneId, kind: 'creation', name: recipe.name, ...spot,
    params: recipe, story: recipe.story, created_by: createdBy });
  const obj = { ...get('SELECT * FROM objects WHERE id = ?', id), params: recipe };
  emit('object', { object: obj });
  return obj;
}
