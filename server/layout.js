// The starting layout: which places and things the island begins with.
// The Keeper edits world/island-layout.xlsx (sheet "Starting features"); if that file is missing,
// world/starting-layout.json is used instead. Nothing here touches the database.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import AdmZip from 'adm-zip';
import { ROOT } from './config.js';

export const LAYOUT_XLSX = process.env.MEMO_LAYOUT || path.join(ROOT, 'world', 'island-layout.xlsx');
export const LAYOUT_JSON = path.join(ROOT, 'world', 'starting-layout.json');
export const LAND_RADIUS = 33;

// Every kind of thing the browser knows how to draw, either as a built-in shape or as a model
// from web/assets/models. Unknown kinds are kept (a model may arrive later) but reported.
export const KINDS = ['notice_board', 'burrow', 'workshop_hut', 'library_tower', 'computer', 'pond', 'garden_plot',
  'watering_can', 'log_pile', 'lantern', 'bench', 'stump', 'signpost', 'wall', 'driftwood', 'shells', 'tree', 'pine',
  'rock', 'bush', 'flower_patch', 'mushrooms', 'well', 'stone_wall', 'path_stones', 'fence', 'grass_tuft',
  'flower_cluster', 'flower_cluster_gold', 'flower_cluster_blue', 'crate', 'barrel', 'lookout'];
// Asked for by the Keeper and in the layout, but with no shape or model yet. They are kept in the world
// (so a model with the same name shows up as soon as it exists) and simply not drawn until then.
export const AWAITING_MODEL = ['observatory', 'beach_hut', 'waterfall', 'bridge', 'stream', 'campfire'];

// ---------- reading the spreadsheet ----------
const unxml = (s) => s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&apos;/g, "'")
  .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16))).replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
  .replace(/_x000D_/g, '').replace(/&amp;/g, '&');
const texts = (xml) => [...xml.matchAll(/<t(?:\s[^>]*)?>([\s\S]*?)<\/t>/g)].map((m) => unxml(m[1])).join('');
const colIndex = (ref) => { let n = 0; for (const ch of ref.replace(/\d+/g, '')) n = n * 26 + ch.charCodeAt(0) - 64; return n - 1; };

// Returns { sheetName: [[cell, ...], ...] } with strings and numbers. Enough of the format for a plain table.
export function readXlsx(file) {
  const zip = new AdmZip(file), read = (name) => zip.getEntry(name)?.getData().toString('utf8') ?? '';
  const shared = [...read('xl/sharedStrings.xml').matchAll(/<si>([\s\S]*?)<\/si>/g)].map((m) => texts(m[1].replace(/<rPh[\s\S]*?<\/rPh>/g, '')));
  const rels = Object.fromEntries([...read('xl/_rels/workbook.xml.rels').matchAll(/<Relationship\b[^>]*>/g)]
    .map((m) => [/\bId="([^"]+)"/.exec(m[0])?.[1], /\bTarget="([^"]+)"/.exec(m[0])?.[1]]));
  const sheets = {};
  for (const m of read('xl/workbook.xml').matchAll(/<sheet\b[^>]*>/g)) {
    const name = unxml(/\bname="([^"]*)"/.exec(m[0])[1]), target = rels[/\br:id="([^"]+)"/.exec(m[0])[1]];
    if (!target) continue;
    const xml = read(target.startsWith('/') ? target.slice(1) : `xl/${target}`), rows = [];
    for (const r of xml.matchAll(/<row\b[^>]*?(?:\/>|>([\s\S]*?)<\/row>)/g)) {
      const row = [];
      for (const c of (r[1] || '').matchAll(/<c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/c>)/g)) {
        const ref = /\br="([A-Z]+\d+)"/.exec(c[1]), type = /\bt="([^"]+)"/.exec(c[1])?.[1], body = c[2] || '';
        const v = /<v>([\s\S]*?)<\/v>/.exec(body)?.[1];
        let val = '';
        if (type === 's') val = shared[Number(v)] ?? '';
        else if (type === 'inlineStr') val = texts(body);
        else if (type === 'str' || type === 'e') val = unxml(v ?? '');
        else if (type === 'b') val = v === '1';
        else if (v !== undefined && v !== '') val = Number(v);
        row[ref ? colIndex(ref[1]) : row.length] = val;
      }
      rows.push(Array.from(row, (x) => x ?? ''));
    }
    sheets[name] = rows;
  }
  return sheets;
}

const yes = (v) => v === true || /^(y|yes|true|1|x|✓)$/i.test(String(v).trim());
const numOr = (v, d) => (v === '' || v === null || v === undefined || Number.isNaN(Number(v)) ? d : Number(v));
const slug = (s) => String(s).trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
function options(text) {
  const out = {};
  for (const part of String(text || '').split(/[;\n]/)) {
    const m = /^\s*([\w ]+?)\s*[=:]\s*(.+?)\s*$/.exec(part);
    if (!m) continue;
    const v = m[2];
    out[slug(m[1])] = /^(true|yes)$/i.test(v) ? true : /^(false|no)$/i.test(v) ? false : Number.isNaN(Number(v)) ? v : Number(v);
  }
  return out;
}

// Turns the rows of a feature sheet into layout entries. Headers are found by name, so columns can be reordered.
function featureRows(rows, sheet, warn) {
  const head = rows.findIndex((r) => r.some((c) => /^include/i.test(String(c))) && r.some((c) => /^feature/i.test(String(c))));
  if (head < 0) return [];
  const col = (re) => rows[head].findIndex((c) => re.test(String(c).trim()));
  const C = { include: col(/^include/i), feature: col(/^feature/i), type: col(/^type/i), place: col(/^place/i), asset: col(/^asset/i),
    count: col(/^count/i), x: col(/^x\b/i), z: col(/^z\b/i), size: col(/^size/i), facing: col(/^facing/i), options: col(/^options/i),
    sees: col(/^what ash is told/i), gather: col(/^things ash can gather/i) };
  const out = [];
  rows.slice(head + 1).forEach((r, i) => {
    const cell = (k) => (C[k] >= 0 ? r[C[k]] ?? '' : '');
    const type = String(cell('type')).trim().toLowerCase(), feature = String(cell('feature')).trim();
    if (!type || !feature || /^scatter seed/i.test(feature)) return;
    const where = `${sheet} row ${head + i + 2} ("${feature}")`;
    if (!/^(place|thing|scattered)/.test(type)) { warn(`${where}: Type should be Place, Thing or Scattered. Skipped.`); return; }
    out.push({ where, include: yes(cell('include')), type: type.replace(/^(place|thing|scattered).*/, '$1'), feature, place: slug(cell('place')),
      asset: slug(cell('asset')), count: numOr(cell('count'), 1), x: numOr(cell('x'), 0), z: numOr(cell('z'), 0), size: numOr(cell('size'), null),
      facing: numOr(cell('facing'), 0), options: options(cell('options')), sees: String(cell('sees')).trim(),
      gather: String(cell('gather')).split(/[,;\n]/).map((s) => s.trim().toLowerCase()).filter(Boolean) });
  });
  return out;
}

export function layoutFromSheets(sheets, warn = () => {}) {
  const rows = [];
  for (const [name, data] of Object.entries(sheets)) if (/^(starting features|ideas)/i.test(name)) rows.push(...featureRows(data, name, warn));
  if (!rows.length) throw new Error('No "Starting features" sheet with Include and Feature columns was found.');
  const layout = { version: 1, scatterSeed: 20261117, places: [], things: [], scatter: [] };
  const settings = sheets[Object.keys(sheets).find((n) => /^starting features/i.test(n))] || [];
  for (const r of settings) if (/^scatter seed/i.test(String(r[0])) || /^scatter seed/i.test(String(r[1]))) layout.scatterSeed = numOr(r.find((c) => typeof c === 'number'), layout.scatterSeed);
  const off = new Set();
  for (const r of rows.filter((x) => x.type === 'place')) {
    const id = r.place || slug(r.feature);
    if (!r.include) { off.add(id); continue; }
    if (layout.places.some((p) => p.id === id)) { warn(`${r.where}: there is already a place with the id "${id}". Skipped.`); continue; }
    const p = { id, name: r.feature, x: r.x, z: r.z, radius: Math.max(1.5, r.size ?? 5), description: r.sees || `A place called ${r.feature}.`, gatherables: r.gather };
    if (r.options.ground_lift) { p.lift = r.options.ground_lift; p.liftRadius = r.options.lift_width || p.radius; }
    if (r.options.ash_starts_here) layout.start = { place: id, x: 3.2, z: 2.8 };
    layout.places.push(p);
  }
  const has = (id) => layout.places.some((p) => p.id === id), waiting = new Set();
  for (const r of rows.filter((x) => x.type !== 'place')) {
    if (!r.include) continue;
    if (r.place && !has(r.place)) { if (!off.has(r.place)) warn(`${r.where}: its place "${r.place}" is not in the list, so it was left out.`); continue; }
    if (!r.asset) { warn(`${r.where}: no Asset chosen. Skipped.`); continue; }
    if (AWAITING_MODEL.includes(r.asset)) waiting.add(r.asset);
    else if (!KINDS.includes(r.asset)) warn(`${r.where}: "${r.asset}" is not an asset the game knows. It will only show if a model with that name exists.`);
    if (r.type === 'scattered') {
      const o = r.options;
      layout.scatter.push({ kind: r.asset, count: Math.max(0, Math.round(r.count)), ...(o.in_clumps_of ? { clumpOf: o.in_clumps_of } : {}),
        rMin: o.nearest ?? 4, rMax: Math.min(LAND_RADIUS, o.farthest ?? 30), scaleMin: o.smallest ?? 0.75, scaleMax: o.biggest ?? 1.35, ...(r.place ? { place: r.place } : {}) });
    } else {
      const params = { ...r.options };
      for (const k of Object.keys(params)) if (k.endsWith('_deg')) { params[k.slice(0, -4)] = (params[k] * Math.PI) / 180; delete params[k]; }
      const label = params.label; delete params.label;
      layout.things.push({ kind: r.asset, ...(label ? { name: r.feature } : {}), ...(r.place ? { place: r.place } : {}), x: r.x, z: r.z, facing: r.facing, scale: r.size ?? 1, params });
    }
  }
  if (waiting.size) warn(`Not drawn yet, waiting for models: ${[...waiting].join(', ')}. Everything else about them already works.`);
  return layout;
}

// ---------- loading ----------
export function loadLayout({ file, log = console.warn } = {}) {
  const warnings = [], warn = (m) => warnings.push(m);
  let layout, source;
  const xlsx = file || LAYOUT_XLSX;
  if (fs.existsSync(xlsx) && /\.xlsx$/i.test(xlsx)) {
    try { layout = layoutFromSheets(readXlsx(xlsx), warn); source = xlsx; }
    catch (e) { warn(`Could not read ${path.basename(xlsx)} (${e.message}). Using the saved layout instead.`); }
  }
  if (!layout) { layout = source = /\.json$/i.test(xlsx) && fs.existsSync(xlsx) ? xlsx : LAYOUT_JSON; layout = JSON.parse(fs.readFileSync(source, 'utf8')); }
  layout.places ||= []; layout.things ||= []; layout.scatter ||= [];
  if (!layout.places.length) throw new Error('The layout has no places. Ash needs at least one place to stand.');
  for (const p of layout.places) if (Math.hypot(p.x, p.z) + p.radius * 0.5 > LAND_RADIUS + 1) warn(`"${p.name}" reaches past the edge of the land (the island is about ${LAND_RADIUS} m from centre to grass edge).`);
  for (const a of layout.places) for (const b of layout.places) if (a.id < b.id && Math.hypot(a.x - b.x, a.z - b.z) < (a.radius + b.radius) * 0.5) warn(`"${a.name}" and "${b.name}" sit almost on top of each other.`);
  const kinds = new Set(layout.things.map((t) => t.kind));
  if (!kinds.has('notice_board')) warn('No notice board: Ash cannot pin wishes or open parcels from you.');
  if (!kinds.has('burrow')) warn('No den: Ash will sleep wherever he happens to be.');
  if (!kinds.has('computer')) warn('No computer: Ash has no Claude, Wikipedia, browser, GitHub or text editor.');
  if (!kinds.has('library_tower')) warn('No library: Ash cannot read your books.');
  if (!layout.start || !layout.places.some((p) => p.id === layout.start.place)) {
    const home = layout.things.find((t) => t.kind === 'burrow' && t.place)?.place || layout.places[0].id;
    layout.start = { place: home, x: 3.2, z: 2.8 };
  }
  for (const w of warnings) log?.(`[layout] ${w}`);
  return { layout, warnings, source, hash: crypto.createHash('sha1').update(JSON.stringify(layout)).digest('hex') };
}

// ---------- from layout to the actual places and objects ----------
// Small seeded random so the island is the same every time it is created.
function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const SCATTER_PARAMS = {
  tree: (rand) => ({ hue: rand() }), pine: (rand) => ({ hue: rand() }),
  rock: (rand) => ({ seed: Math.floor(rand() * 1e6) }),
  bush: (rand) => ({ hue: rand(), berries: rand() > 0.6 }),
  flower_patch: (rand) => ({ count: 5 + Math.floor(rand() * 6), spread: 1.4 }),
};

export function expandLayout(layout) {
  const zones = layout.places.map((p) => ({ id: p.id, name: p.name, description: p.description, x: p.x, z: p.z, radius: p.radius, gatherables: p.gatherables || [] }));
  const Z = Object.fromEntries(zones.map((z) => [z.id, z])), objects = [];
  for (const t of layout.things) {
    const c = t.place ? Z[t.place] : { x: 0, z: 0 };
    if (!c) continue;
    objects.push({ zone_id: t.place || null, kind: t.kind, name: t.name || null, x: c.x + (t.x || 0), z: c.z + (t.z || 0),
      rot: ((t.facing || 0) * Math.PI) / 180, scale: t.scale ?? 1, params: t.params || {} });
  }
  // Scattered scenery, kept clear of the middles of the places. Trees can grow in clumps.
  const rand = rng(layout.scatterSeed ?? 20261117);
  const clear = (x, z, pad = 0.7) => zones.every((zn) => Math.hypot(x - zn.x, z - zn.z) > zn.radius * pad);
  for (const s of layout.scatter) {
    const mk = SCATTER_PARAMS[s.kind] || (() => ({})), span = s.scaleMax - s.scaleMin;
    const c = s.place ? Z[s.place] : { x: 0, z: 0 };
    if (!c) continue;
    const ok = (x, z, pad) => (s.place ? Math.hypot(x, z) < LAND_RADIUS : clear(x, z, pad));
    if (s.clumpOf) {
      const groups = Math.ceil(s.count / s.clumpOf);
      for (let g = 0, guard = 0; g < groups && guard < 400; guard++) {
        const a = rand() * Math.PI * 2, r = s.rMin + Math.sqrt(rand()) * (s.rMax - s.rMin), cx = c.x + Math.cos(a) * r, cz = c.z + Math.sin(a) * r;
        if (!ok(cx, cz, 1.0)) continue;
        g++;
        for (let i = 0; i < s.clumpOf; i++) {
          const x = cx + (rand() - 0.5) * 5.5, z = cz + (rand() - 0.5) * 5.5;
          if (ok(x, z, 0.85)) objects.push({ zone_id: null, kind: s.kind, name: null, x, z, rot: rand() * Math.PI * 2, scale: s.scaleMin + rand() * span, params: mk(rand) });
        }
      }
    } else {
      let placed = 0, guard = 0;
      while (placed < s.count && guard++ < s.count * 40) {
        const a = rand() * Math.PI * 2, r = s.rMin + Math.sqrt(rand()) * (s.rMax - s.rMin), x = c.x + Math.cos(a) * r, z = c.z + Math.sin(a) * r;
        if (!ok(x, z)) continue;
        objects.push({ zone_id: null, kind: s.kind, name: null, x, z, rot: rand() * Math.PI * 2, scale: s.scaleMin + rand() * span, params: mk(rand) });
        placed++;
      }
    }
  }
  // Ground shaping that belongs to a place (the lookout's hill, the pond's hollow) moves with it.
  const terrain = layout.places.filter((p) => p.lift).map((p) => ({ x: p.x, z: p.z, lift: p.lift, radius: p.liftRadius || p.radius }));
  const s = Z[layout.start.place];
  return { zones, objects, terrain, start: { zone: s.id, x: s.x + layout.start.x, z: s.z + layout.start.z } };
}

// ---------- a top-down picture, so the numbers make sense ----------
const COLOURS = { tree: '#6fab52', pine: '#4f8a55', bush: '#9ccf73', rock: '#a9a394', flower_patch: '#f4a6c0', mushrooms: '#d1495b' };
export function mapSvg(layout) {
  const { zones, objects } = expandLayout(layout), S = 12, half = 42, px = (v) => ((v + half) * S).toFixed(1);
  const coast = (R) => Array.from({ length: 181 }, (_, i) => { const a = (i / 180) * Math.PI * 2, r = R * (1 + 0.07 * Math.sin(3 * a + 1) + 0.045 * Math.sin(5 * a + 2.3) + 0.03 * Math.sin(9 * a)); return `${px(Math.cos(a) * r)},${px(Math.sin(a) * r)}`; }).join(' ');
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const out = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${half * 2 * S} ${half * 2 * S}" font-family="Arial, sans-serif">`,
    `<rect width="100%" height="100%" fill="#8fd0cd"/>`, `<polygon points="${coast(36)}" fill="#f3e3bd"/>`, `<polygon points="${coast(32)}" fill="#a9d57c"/>`];
  for (let v = -40; v <= 40; v += 10) {
    out.push(`<line x1="${px(v)}" y1="0" x2="${px(v)}" y2="${half * 2 * S}" stroke="#00000018"/>`, `<line x1="0" y1="${px(v)}" x2="${half * 2 * S}" y2="${px(v)}" stroke="#00000018"/>`,
      `<text x="${px(v)}" y="14" font-size="11" text-anchor="middle" fill="#245">x ${v}</text>`, `<text x="4" y="${px(v)}" font-size="11" dy="4" fill="#245">z ${v}</text>`);
  }
  const hub = zones.find((z) => z.id === 'board');
  if (hub) for (const z of zones) if (z !== hub) out.push(`<line x1="${px(hub.x)}" y1="${px(hub.z)}" x2="${px(z.x)}" y2="${px(z.z)}" stroke="#ead3a4" stroke-width="7" stroke-linecap="round"/>`);
  for (const o of objects.filter((x) => x.kind === 'stream')) {
    const pts = [o.params.from, ...String(o.params.via || '').split(','), o.params.to].map((id) => zones.find((z) => z.id === String(id).trim())).filter(Boolean);
    if (pts.length > 1) out.push(`<polyline points="${pts.map((z) => `${px(z.x)},${px(z.z)}`).join(' ')}" fill="none" stroke="#4fb3c8" stroke-width="${(o.params.width || 1.2) * S * 0.6}" stroke-linecap="round" stroke-linejoin="round"/>`);
  }
  for (const z of zones) out.push(`<circle cx="${px(z.x)}" cy="${px(z.z)}" r="${z.radius * S}" fill="#ffffff55" stroke="#7a5c3a" stroke-width="1.5" stroke-dasharray="6 4"/>`);
  for (const o of objects) {
    if (o.kind === 'wall' || o.kind === 'stream') continue;
    const scen = COLOURS[o.kind];
    if (scen) out.push(`<circle cx="${px(o.x)}" cy="${px(o.z)}" r="${(o.kind === 'tree' || o.kind === 'pine' ? 1.3 : 0.6) * o.scale * S}" fill="${scen}" fill-opacity="0.75"/>`);
    else if (o.kind === 'pond') out.push(`<circle cx="${px(o.x)}" cy="${px(o.z)}" r="${(o.params.radius || 4.5) * o.scale * S}" fill="#6fc3c4"/>`);
    else out.push(`<rect x="${px(o.x) - 5}" y="${px(o.z) - 5}" width="10" height="10" rx="2" fill="#8a5a3c" stroke="#fff"/>`);
  }
  for (const z of zones) {
    const top = Number(px(z.z)) - z.radius * S;
    out.push(`<text x="${px(z.x)}" y="${(top - 5).toFixed(1)}" font-size="16" font-weight="bold" text-anchor="middle" fill="#3b2a1a" stroke="#fff" stroke-width="4" paint-order="stroke">${esc(z.name)}</text>`,
      `<text x="${px(z.x)}" y="${(top + 14).toFixed(1)}" font-size="11" text-anchor="middle" fill="#3b2a1a" stroke="#fff" stroke-width="3" paint-order="stroke">x ${z.x}, z ${z.z}</text>`);
  }
  out.push(`<text x="${half * S}" y="${half * 2 * S - 10}" font-size="13" text-anchor="middle" fill="#134">Top-down view. 1 square = 10 m. Brown squares are placed things, dots are scattered scenery, dashed rings are places.</text>`, '</svg>');
  return out.join('\n');
}
