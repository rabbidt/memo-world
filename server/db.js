import fs from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { config } from './config.js';

fs.mkdirSync(path.dirname(config.dbPath), { recursive: true });
export const db = new DatabaseSync(config.dbPath);
db.exec('PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS zones (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
  x REAL NOT NULL, z REAL NOT NULL, radius REAL NOT NULL,
  gatherables TEXT NOT NULL DEFAULT '[]'
);
-- Everything standing in the world: scenery, buildings, and Ash's creations.
CREATE TABLE IF NOT EXISTS objects (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zone_id TEXT, kind TEXT NOT NULL, name TEXT,
  x REAL NOT NULL, z REAL NOT NULL, rot REAL NOT NULL DEFAULT 0, scale REAL NOT NULL DEFAULT 1,
  params TEXT NOT NULL DEFAULT '{}',   -- builder parameters, or the recipe for a creation
  story TEXT, created_by TEXT NOT NULL DEFAULT 'world', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
  name TEXT PRIMARY KEY, qty INTEGER NOT NULL, source TEXT, note TEXT, updated_at TEXT NOT NULL
);
-- Append-only memory stream.
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, type TEXT NOT NULL,
  summary TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}', importance INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS events_ts ON events(ts);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, title TEXT NOT NULL,
  body TEXT NOT NULL, english TEXT, mood TEXT, kind TEXT NOT NULL DEFAULT 'entry'
);
CREATE TABLE IF NOT EXISTS wishes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, text TEXT NOT NULL, english TEXT, reason TEXT,
  status TEXT NOT NULL DEFAULT 'open', reply TEXT, answered_at TEXT,
  project_id INTEGER, supply TEXT, qty INTEGER
);
CREATE TABLE IF NOT EXISTS gifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, name TEXT NOT NULL, note TEXT,
  wish_id INTEGER, project_id INTEGER, qty INTEGER NOT NULL DEFAULT 1,
  from_name TEXT NOT NULL DEFAULT 'the Keeper', invite TEXT,
  kind TEXT NOT NULL DEFAULT 'item', description TEXT,  -- kind: item | pet | special
  status TEXT NOT NULL DEFAULT 'waiting', opened_at TEXT
);
-- What nightly reflection distils from the event log.
CREATE TABLE IF NOT EXISTS beliefs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, text TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS spend (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, month TEXT NOT NULL, model TEXT NOT NULL,
  purpose TEXT NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL,
  cache_read INTEGER NOT NULL DEFAULT 0, cache_write INTEGER NOT NULL DEFAULT 0, cost_usd REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS spend_month ON spend(month);
-- Town building: big builds wait as a site until the Keeper has sent the supplies.
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, name TEXT NOT NULL, purpose TEXT,
  zone_id TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'planned',  -- planned | built | abandoned
  recipe TEXT NOT NULL, supplies TEXT NOT NULL,                   -- supplies: [{name, qty, have}]
  site_object_id INTEGER, built_object_id INTEGER, built_at TEXT
);
-- The audit of everything Ash does on his computer. Append-only: the triggers below make
-- changing or deleting a row impossible, for Ash and for everyone else.
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, app TEXT NOT NULL, action TEXT NOT NULL,
  query TEXT NOT NULL, reason TEXT, status TEXT NOT NULL, summary TEXT,
  sources TEXT NOT NULL DEFAULT '[]', cost_usd REAL NOT NULL DEFAULT 0
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT, 'the audit log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT, 'the audit log is append-only'); END;
-- The apps on Ash's computer. Only the Keeper can switch one on or off.
CREATE TABLE IF NOT EXISTS apps (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
);
-- Longer things Ash writes in his text editor.
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, updated_at TEXT NOT NULL, title TEXT NOT NULL,
  body TEXT NOT NULL, english TEXT
);
-- Books from the Keeper's own collection (the books folder), and Ash's place and notes in them.
CREATE TABLE IF NOT EXISTS books (
  id INTEGER PRIMARY KEY AUTOINCREMENT, file TEXT UNIQUE NOT NULL, title TEXT NOT NULL, chars INTEGER NOT NULL,
  position INTEGER NOT NULL DEFAULT 0, started_at TEXT, finished_at TEXT, added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS book_notes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL, ts TEXT NOT NULL, position INTEGER NOT NULL,
  note TEXT NOT NULL, english TEXT
);
-- Shareable visitor links. The Keeper can revoke any of them.
CREATE TABLE IF NOT EXISTS invites (
  token TEXT PRIMARY KEY, label TEXT NOT NULL, created_at TEXT NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
);
-- Programs and games Ash writes at his computer. They only ever run in a browser sandbox.
CREATE TABLE IF NOT EXISTS programs (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, name TEXT NOT NULL, kind TEXT NOT NULL,
  description TEXT, english TEXT, html TEXT NOT NULL, object_id INTEGER, commit_url TEXT, plays INTEGER NOT NULL DEFAULT 0
);
-- Notes between Ash and the Keeper.
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, sender TEXT NOT NULL, text TEXT NOT NULL, english TEXT,
  seen INTEGER NOT NULL DEFAULT 0
);
`);

export const all = (sql, ...p) => db.prepare(sql).all(...p);
export const get = (sql, ...p) => db.prepare(sql).get(...p);
export const run = (sql, ...p) => db.prepare(sql).run(...p);
export const nowIso = () => new Date().toISOString();

export function getState(key, fallback = null) {
  const row = get('SELECT value FROM state WHERE key = ?', key);
  return row ? JSON.parse(row.value) : fallback;
}
export function setState(key, value) {
  run('INSERT INTO state(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
    key, JSON.stringify(value));
}

const listeners = new Set();
export const onChange = (fn) => { listeners.add(fn); return () => listeners.delete(fn); };
export const emit = (type, payload = {}) => { for (const fn of listeners) fn({ type, ...payload }); };

export function logEvent(type, summary, data = {}, importance = 1) {
  const ts = nowIso();
  const r = run('INSERT INTO events(ts, type, summary, data, importance) VALUES(?,?,?,?,?)',
    ts, type, summary, JSON.stringify(data), importance);
  const ev = { id: Number(r.lastInsertRowid), ts, type, summary, data, importance };
  emit('event', { event: ev });
  return ev;
}
