import path from 'node:path';
import crypto from 'node:crypto';
import express from 'express';
import { config, demoMode, ROOT } from './config.js';
import { all, get, run, nowIso, getState, setState, onChange, emit, logEvent } from './db.js';
import { seedWorld, getZones, getObjects, getInventory, getMemo } from './world.js';
import { budgetSummary } from './budget.js';
import { heartbeat, getNeeds, maturity, lifeStage, activeProject, localDay } from './brain.js';
import { blockedReason, cleanText } from './filter.js';
import { seedApps, getApps, scanBooks } from './computer.js';

seedWorld();
seedApps();
scanBooks();
setInterval(scanBooks, 10 * 60000).unref();
if (!getState('owner_key')) setState('owner_key', crypto.randomBytes(18).toString('hex'));
const OWNER_KEY = getState('owner_key');

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '20kb' }));

// ---------- who is asking: the Keeper (owner key), a visitor (invite link), or nobody ----------
function whoIs(req) {
  const key = String(req.get('x-memo-key') || req.query.k || '');
  if (!key) return null;
  const a = Buffer.from(key), b = Buffer.from(OWNER_KEY);
  if (a.length === b.length && crypto.timingSafeEqual(a, b)) return { role: 'owner', label: 'the Keeper' };
  const inv = get('SELECT * FROM invites WHERE token = ? AND revoked = 0', key);
  return inv ? { role: 'visitor', label: inv.label, token: inv.token } : null;
}
const anyone = (req, res, next) => { req.who = whoIs(req); return req.who ? next() : res.status(401).json({ error: 'This island is private. You need a link from its Keeper.' }); };
const owner = (req, res, next) => { req.who = whoIs(req); return req.who?.role === 'owner' ? next() : res.status(403).json({ error: 'Only the Keeper can do that.' }); };

// ---------- static files ----------
app.use('/vendor/three/', express.static(path.join(ROOT, 'node_modules/three/build')));
app.use('/vendor/three-addons/', express.static(path.join(ROOT, 'node_modules/three/examples/jsm')));
app.use('/vendor/marked.js', express.static(path.join(ROOT, 'node_modules/marked/lib/marked.esm.js')));
app.use('/vendor/purify.js', express.static(path.join(ROOT, 'node_modules/dompurify/dist/purify.es.mjs')));
app.use(express.static(path.join(ROOT, 'web')));

// ---------- reading the world ----------
const memoView = () => {
  const m = maturity();
  return { ...getMemo(), needs: getNeeds(), maturity: m, stage: lifeStage(m).name };
};
const programsView = () => all('SELECT id, ts, name, kind, description, english, object_id, commit_url, plays FROM programs ORDER BY id DESC');
const status = () => ({ demo: demoMode(), brain: getState('brain_status', { ok: true }), tickMinutes: config.tickMinutes,
  bedtimeMin: config.bedtimeMin, wakeMin: config.wakeMin, lastTick: getState('last_tick', 0) });

app.get('/api/me', anyone, (req, res) => res.json({ role: req.who.role, label: req.who.label }));
app.get('/api/world', anyone, (req, res) => res.json({
  zones: getZones(), objects: getObjects(), memo: memoView(), inventory: getInventory(),
  parcels: all("SELECT id, from_name, kind FROM gifts WHERE status = 'waiting'"),
  project: activeProject(), programs: programsView(), status: status(),
  budget: req.who.role === 'owner' ? budgetSummary() : null,
}));
app.get('/api/journal', anyone, (req, res) => res.json(all('SELECT * FROM journal ORDER BY id DESC LIMIT 60')));
app.get('/api/wishes', anyone, (req, res) => res.json(all('SELECT * FROM wishes ORDER BY id DESC LIMIT 60')));
app.get('/api/events', anyone, (req, res) => res.json(all('SELECT id, ts, type, summary FROM events ORDER BY id DESC LIMIT 60')));
app.get('/api/mind', anyone, (req, res) => res.json(all('SELECT id, kind, text, created_at FROM beliefs WHERE active = 1 ORDER BY kind, id')));
app.get('/api/messages', owner, (req, res) => res.json(all('SELECT * FROM messages ORDER BY id DESC LIMIT 80')));
// The audit of Memo's computer: searchable, filterable, and read-only for everyone.
app.get('/api/audit', owner, (req, res) => {
  const q = `%${String(req.query.q || '').slice(0, 80)}%`, appId = String(req.query.app || '');
  res.json(all(`SELECT * FROM audit WHERE (query LIKE ? OR summary LIKE ? OR reason LIKE ? OR status LIKE ?) AND (? = '' OR app = ?) ORDER BY id DESC LIMIT 300`,
    q, q, q, q, appId, appId).map((w) => ({ ...w, sources: JSON.parse(w.sources) })));
});
app.get('/api/apps', owner, (req, res) => res.json(getApps()));
app.post('/api/apps/:id', owner, (req, res) => {
  run('UPDATE apps SET enabled = ? WHERE id = ?', req.body?.enabled ? 1 : 0, req.params.id);
  res.json(getApps());
});
// Memo's writing is for everyone to read. The Keeper's books are not: visitors never see them,
// and no route serves a book's text at all.
app.get('/api/documents', anyone, (req, res) => res.json(all('SELECT * FROM documents ORDER BY updated_at DESC LIMIT 60')));
app.get('/api/books', owner, (req, res) => res.json({
  folder: config.booksDir,
  books: all('SELECT id, title, chars, position, started_at, finished_at FROM books ORDER BY (started_at IS NULL), started_at DESC'),
  notes: all('SELECT n.*, b.title FROM book_notes n JOIN books b ON b.id = n.book_id ORDER BY n.id DESC LIMIT 60'),
}));
app.post('/api/books/scan', owner, (req, res) => { scanBooks(); res.json({ ok: true }); });
app.get('/api/budget', owner, (req, res) => res.json(budgetSummary()));

// Memo's programs run only here: in the visitor's browser, inside a locked sandbox with no
// network, no cookies and no way to reach the page around it. Never on this computer.
app.get('/api/programs/:id/run', anyone, (req, res) => {
  const p = get('SELECT html FROM programs WHERE id = ?', Number(req.params.id));
  if (!p) return res.status(404).send('No such program.');
  res.set('Content-Security-Policy', "sandbox allow-scripts; default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data:; media-src data:");
  res.set('X-Content-Type-Options', 'nosniff');
  res.type('html').send(p.html);
});

// ---------- gifts, wishes, notes ----------
const today = () => `${localDay()}`;
const giftsToday = (where, ...p) => get(`SELECT COUNT(*) AS n FROM gifts WHERE substr(ts, 1, 10) = substr(?, 1, 10) AND ${where}`, nowIso(), ...p).n;

app.post('/api/gifts', anyone, (req, res) => {
  const visitor = req.who.role === 'visitor';
  const b = req.body || {};
  let name = cleanText(b.name, 60), note = cleanText(b.note, 200), description = cleanText(b.description, 300);
  let kind = ['item', 'pet', 'special'].includes(b.kind) ? b.kind : 'item';
  let qty = 1, projectId = null;
  const wish = b.wish_id ? get("SELECT * FROM wishes WHERE id = ? AND status = 'open'", Number(b.wish_id)) : null;
  if (b.wish_id && !wish) return res.status(404).json({ error: 'That wish is no longer open.' });
  if (wish?.project_id) { name = wish.supply; qty = wish.qty || 1; projectId = wish.project_id; kind = 'item'; }
  if (visitor) {
    kind = 'item'; description = '';
    if (giftsToday('invite = ?', req.who.token) >= 3) return res.status(429).json({ error: 'You have left three gifts today. Come back tomorrow!' });
    if (giftsToday('invite IS NOT NULL') >= 12) return res.status(429).json({ error: 'Memo has had plenty of visitor gifts today. Try tomorrow.' });
  }
  if (!name) return res.status(400).json({ error: 'A gift needs a name.' });
  if (blockedReason(`${name} ${note} ${description}`)) return res.status(400).json({ error: 'Please keep gifts gentle. That one cannot be left here.' });
  if (get("SELECT COUNT(*) AS n FROM gifts WHERE status = 'waiting'").n >= 10) return res.status(429).json({ error: 'There are already a lot of parcels waiting. Let Memo open some first.' });
  const from = visitor ? `a visitor called ${cleanText(req.who.label, 30)}` : 'the Keeper';
  run('INSERT INTO gifts(ts, name, note, wish_id, project_id, qty, from_name, invite, kind, description) VALUES(?,?,?,?,?,?,?,?,?,?)',
    nowIso(), name.toLowerCase(), note || null, wish?.id ?? null, projectId, qty, from, visitor ? req.who.token : null, kind, description || null);
  if (wish) {
    run("UPDATE wishes SET status = 'granted', reply = ?, answered_at = ? WHERE id = ?", note || null, nowIso(), wish.id);
    emit('wishes');
  }
  emit('gifts');
  res.json({ ok: true });
});

app.post('/api/wishes/:id/decline', owner, (req, res) => {
  const wish = get("SELECT * FROM wishes WHERE id = ? AND status = 'open'", Number(req.params.id));
  if (!wish) return res.status(404).json({ error: 'That wish is no longer open.' });
  const note = cleanText(req.body?.note, 200);
  run("UPDATE wishes SET status = 'declined', reply = ?, answered_at = ? WHERE id = ?", note || null, nowIso(), wish.id);
  logEvent('wish', `The Keeper answered my wish "${(wish.english || wish.text).slice(0, 100)}": not this time.${note ? ` "${note}"` : ''}`, {}, 3);
  emit('wishes');
  res.json({ ok: true });
});

app.post('/api/messages', owner, (req, res) => {
  const text = cleanText(req.body?.text, 400);
  if (!text) return res.status(400).json({ error: 'Write something first.' });
  run("INSERT INTO messages(ts, sender, text) VALUES(?, 'keeper', ?)", nowIso(), text);
  emit('messages');
  res.json({ ok: true });
});

app.post('/api/programs/:id/played', anyone, (req, res) => {
  run('UPDATE programs SET plays = plays + 1 WHERE id = ?', Number(req.params.id));
  res.json({ ok: true });
});

// ---------- Keeper only: visitor links and a nudge ----------
app.get('/api/invites', owner, (req, res) => res.json(all('SELECT * FROM invites ORDER BY created_at DESC')));
app.post('/api/invites', owner, (req, res) => {
  const label = cleanText(req.body?.label, 30) || 'friend';
  if (blockedReason(label)) return res.status(400).json({ error: 'Pick a different name.' });
  const token = crypto.randomBytes(12).toString('hex');
  run('INSERT INTO invites(token, label, created_at) VALUES(?,?,?)', token, label, nowIso());
  res.json({ token, label });
});
app.post('/api/invites/:token/revoke', owner, (req, res) => {
  run('UPDATE invites SET revoked = 1 WHERE token = ?', req.params.token);
  for (const c of clients) if (c.who.token === req.params.token) c.res.end();
  res.json({ ok: true });
});
let lastPoke = 0;
app.post('/api/poke', owner, async (req, res) => {
  if (Date.now() - lastPoke < 20000) return res.status(429).json({ error: 'Give Memo a moment.' });
  lastPoke = Date.now();
  res.json({ result: await heartbeat(true) });
});

// ---------- live updates ----------
const clients = new Set();
const OWNER_ONLY = new Set(['messages', 'web', 'budget', 'status', 'books']);
app.get('/api/stream', anyone, (req, res) => {
  res.set({ 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', Connection: 'keep-alive', 'X-Accel-Buffering': 'no' });
  res.flushHeaders();
  res.write('retry: 4000\n\n');
  const c = { res, who: req.who };
  clients.add(c);
  req.on('close', () => clients.delete(c));
});
onChange((msg) => {
  if (msg.type === 'memo') msg = { type: 'memo', memo: memoView() };
  const line = `data: ${JSON.stringify(msg)}\n\n`;
  for (const c of clients) if (c.who.role === 'owner' || !OWNER_ONLY.has(msg.type)) c.res.write(line);
});
setInterval(() => { for (const c of clients) c.res.write(': hi\n\n'); }, 25000).unref();

app.use((err, req, res, next) => { console.error(err); res.status(500).json({ error: 'Something went wrong on the island.' }); });

app.listen(config.port, config.host, () => {
  const base = `http://localhost:${config.port}`;
  console.log(`\n  Memo's island is running.\n\n  Your Keeper link (keep it private):\n    ${base}/?k=${OWNER_KEY}\n`);
  console.log(demoMode()
    ? '  Demo mode: no API key found, so Memo is running on simple instincts (free).\n  Add ANTHROPIC_API_KEY to .env and restart to wake his real mind.\n'
    : `  Brain: ${config.tickModel} every ${config.tickMinutes} min, ${config.deepModel} for making and reflecting.\n  Monthly cap: $${config.monthlyCapUsd}.\n`);
  const beat = () => heartbeat().catch((e) => console.error('[memo] heartbeat failed:', e));
  setTimeout(beat, 3000);
  setInterval(beat, 20000);
});
