// The world is data: zones and objects live in SQLite, and the browser builds whatever it finds.
import { db, all, get, run, nowIso, getState, setState, emit } from './db.js';

import { loadLayout, expandLayout, LAND_RADIUS } from './layout.js';

function addObject(o) {
  const r = run(`INSERT INTO objects(zone_id, kind, name, x, z, rot, scale, params, story, created_by, created_at)
    VALUES(?,?,?,?,?,?,?,?,?,?,?)`,
    o.zone_id ?? null, o.kind, o.name ?? null, o.x, o.z, o.rot ?? 0, o.scale ?? 1,
    JSON.stringify(o.params ?? {}), o.story ?? null, o.created_by ?? 'world', nowIso());
  return Number(r.lastInsertRowid);
}

// The island starts from the Keeper's layout (world/island-layout.xlsx, see server/layout.js).
// On a fresh database that is the whole world. Later, if the layout file has changed, the places and
// the starting things are laid out again; everything Ash made, his pets, parcels and gifts are kept.
export function seedWorld() {
  const { layout, hash } = loadLayout();
  const fresh = get('SELECT COUNT(*) AS n FROM zones').n === 0;
  if (!fresh && getState('layout_hash', null) === hash) return;
  const { zones, objects, terrain, start } = expandLayout(layout);
  db.exec('BEGIN');
  try {
    run("DELETE FROM objects WHERE created_by = 'layout' OR (created_by = 'world' AND kind NOT IN ('pet', 'creation', 'build_site'))");
    const keep = new Set(zones.map((z) => z.id));
    for (const z of all('SELECT id FROM zones')) if (!keep.has(z.id)) run('DELETE FROM zones WHERE id = ?', z.id);
    for (const z of zones) {
      run(`INSERT INTO zones(id, name, description, x, z, radius, gatherables) VALUES(?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET name = excluded.name, description = excluded.description, x = excluded.x, z = excluded.z,
        radius = excluded.radius, gatherables = excluded.gatherables`, z.id, z.name, z.description, z.x, z.z, z.radius, JSON.stringify(z.gatherables));
    }
    for (const o of objects) addObject({ ...o, created_by: 'layout' });
    // Anything of Ash's that stood in a place which no longer exists moves to where he starts.
    run(`UPDATE objects SET zone_id = ?, x = ? + (id % 5) - 2, z = ? + (id % 3) - 1 WHERE zone_id IS NOT NULL AND zone_id NOT IN (SELECT id FROM zones)`, start.zone, start.x, start.z);
    run('UPDATE projects SET zone_id = ? WHERE zone_id NOT IN (SELECT id FROM zones)', start.zone);
    setState('layout_hash', hash); setState('terrain', terrain);
    if (fresh) {
      setState('memo', {
        ...start, activity: 'idle', mood: 'curious',
        energy: 80, thoughtEnglish: 'Oh. A whole island. Where should I look first?', thought: 'Oh. A whole island. Where should I look first?', asleep: false, napUntil: null,
      });
      setState('born_at', nowIso());
    } else {
      const memo = getState('memo');
      if (memo) { const z = zones.find((zn) => zn.id === memo.zone); setState('memo', { ...memo, ...(z ? { x: z.x + z.radius * 0.6, z: z.z + z.radius * 0.3 } : start) }); }
    }
    db.exec('COMMIT');
  } catch (e) { db.exec('ROLLBACK'); throw e; }
  if (!fresh) console.log('[layout] The island layout file changed, so the places and starting things were laid out again.');
}

export const getTerrain = () => getState('terrain', []);
// Where a feature lives: the place holding the first starting thing of that kind (the notice board,
// the den, the computer, the library), or null if the island has none.
export function featureZone(kind) {
  return get("SELECT zone_id FROM objects WHERE kind = ? AND zone_id IS NOT NULL AND created_by IN ('layout', 'world') ORDER BY id LIMIT 1", kind)?.zone_id ?? null;
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
      if (Math.hypot(x, z) < LAND_RADIUS && others.every((o) => Math.hypot(o.x - x, o.z - z) > gap)) return { x, z, rot: a + Math.PI };
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
