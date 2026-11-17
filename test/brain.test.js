// End-to-end check of Ash's mind with a scripted stand-in for Claude (no API key, no cost).
// Run with: npm test
// It works in a fresh folder under the system temp directory and leaves it there afterwards.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import Anthropic from '@anthropic-ai/sdk';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'memo-test-'));
fs.mkdirSync(path.join(tmp, 'books'));
fs.writeFileSync(path.join(tmp, 'books', 'the-quiet-tide.txt'), 'The tide came in slowly. '.repeat(400));
Object.assign(process.env, {
  MEMO_DB: path.join(tmp, 'memo.db'), MEMO_BOOKS_DIR: path.join(tmp, 'books'), ANTHROPIC_API_KEY: 'test-key',
  MEMO_DEMO: '0', MEMO_MONTHLY_CAP_USD: '10', MEMO_KEEPER_FROM_HOUR: '0', MEMO_KEEPER_TO_HOUR: '24',
  MEMO_GITHUB_TOKEN: '', MEMO_NOTIFY_URL: '',
});

// The script: each entry is the list of tool calls "Claude" makes on its next reply.
const script = [];
const calls = [];
let n = 0;
Anthropic.Messages.prototype.create = async function create(params) {
  calls.push(params);
  const names = (params.tools || []).map((t) => t.name);
  const use = (name, input) => ({ type: 'tool_use', id: `toolu_${++n}`, name, input });
  let content;
  if (names.includes('build_object')) {
    const part = { shape: 'box', size: [1, 1, 1], position: [0, 0.5, 0], rotation: [0, 0, 0], color: '#88aa66', material: 'matte' };
    const big = Boolean(params.tools[0].input_schema.properties.supplies);
    const input = {
      name: big ? 'Tide House' : 'Small Wonder', story: 'Moki tala.', story_english: 'A mossy tale.', animation: 'bob',
      parts: [part, { ...part, shape: 'cone', position: [0, 1.5, 0] }, { ...part, size: [99, 99, 99], position: [50, -4, 0], color: 'red', material: 'lava' }],
    };
    if (big) input.supplies = [{ name: 'Planks', qty: 2 }];
    content = [use('build_object', input)];
  } else if (names.includes('save_program')) {
    content = [use('save_program', { name: 'Pebble Hop', description: 'Tiki hop!', english: 'A hopping game.', html: '<!doctype html><title>Pebble Hop</title><button onclick="this.textContent=+this.textContent+1">0</button>' })];
  } else if (names.includes('save_reflection')) {
    content = [use('save_reflection', { title: 'Nala', body: 'Moki day.', english: 'Night. A mossy day.', mood: 'content', goals: ['Finish the Tide House'], interests: ['tides'], beliefs: ['The Keeper is kind'], remember: ['I built my first house.'] })];
  } else if (names.includes('web_search')) content = [{ type: 'text', text: 'Shells are made by sea animals.' }];
  else if (!names.length) content = [{ type: 'text', text: 'Moss is a small soft plant.' }];
  else content = (script.shift() || [['think', { words: 'Mm.', english: 'Mm.', mood: 'calm' }]]).map(([name, input]) => use(name, input));
  return { content, stop_reason: content.some((c) => c.type === 'tool_use') ? 'tool_use' : 'end_turn', usage: { input_tokens: 2000, output_tokens: 300 } };
};

const { seedWorld, getMemo, getInventory } = await import('../server/world.js');
const { seedApps, scanBooks } = await import('../server/computer.js');
const { all, get, run, nowIso } = await import('../server/db.js');
const brain = await import('../server/brain.js');
const { spentThisMonth, monthKey } = await import('../server/budget.js');
seedWorld(); seedApps(); scanBooks();
const think = ['think', { words: 'Tiki.', english: 'Little by little.', mood: 'busy' }];
const moment = async (...turns) => { script.push(...turns); assert.equal(await brain.heartbeat(true), 'ticked'); assert.equal(script.length, 0, 'every scripted turn was used'); };

// 1. Wander, gather, set his own hobby, invent a word.
await moment([['move_to', { zone: 'shore' }], ['gather', { item: 'shell' }]], [['update_mind', { action: 'add', kind: 'hobby', text: 'collecting shells' }], ['update_mind', { action: 'add', kind: 'word', text: 'moki = moss' }], think]);
assert.equal(getMemo().zone, 'shore');
assert.equal(getMemo().thoughtEnglish, 'Little by little.');
assert.ok(getInventory().some((i) => i.name === 'shell'));
assert.equal(all('SELECT * FROM beliefs WHERE active = 1').length, 2);
assert.match(calls.at(-1).messages[0].content, /You feel .* lonely/);
assert.match(calls.at(-1).system, /small wolf/);
assert.match(calls.at(-1).system, /You are a pup/);

// 2. Craft: the recipe is clamped and kept in the world.
await moment([['craft', { idea: 'a shell tower', materials: ['shell'] }]], [think]);
const made = get("SELECT * FROM objects WHERE kind = 'creation'");
const recipe = JSON.parse(made.params);
assert.equal(made.zone_id, 'shore');
assert.ok(recipe.parts.every((p) => p.size.every((v) => v <= 2) && Math.abs(p.position[0]) <= 1.2 && /^#[0-9a-f]{6}$/i.test(p.color)));
assert.equal(recipe.parts[2].material, 'matte');

// 3. Town building: plan, supplies wished for, Keeper sends them, Ash opens and builds.
await moment([['plan_building', { idea: 'a house by the tide' }]], [think]);
const supply = get('SELECT * FROM wishes WHERE project_id IS NOT NULL');
assert.equal(supply.supply, 'planks');
assert.equal(await brain.actions.build({}), 'Still waiting for supplies: 2 planks.');
run("INSERT INTO gifts(ts, name, project_id, qty) VALUES(?, 'planks', ?, 2)", nowIso(), supply.project_id);
await moment([['move_to', { zone: 'board' }], ['open_gift', { gift_id: 1 }]], [think]);
await moment([['move_to', { zone: 'shore' }], ['build', {}]], [think]);
assert.equal(get('SELECT status FROM projects').status, 'built');
assert.equal(get("SELECT COUNT(*) AS n FROM objects WHERE kind = 'build_site'").n, 0);
assert.ok(JSON.parse(get("SELECT params FROM objects WHERE name = 'Tide House'").params).big);

// 4. A pet arrives as a gift and becomes a living thing in the world.
run("INSERT INTO gifts(ts, name, kind, description) VALUES(?, 'a small blue snail', 'pet', 'round and shy')", nowIso());
await moment([['move_to', { zone: 'board' }], ['open_gift', { gift_id: 2 }]], [think]);
const pet = get("SELECT * FROM objects WHERE kind = 'pet'");
assert.ok(pet);
assert.match(await brain.actions.play_with({ pet_id: pet.id }), /You play with|is over at/);

// 5. The computer: only at the library, only listed apps, everything audited, blocked words refused.
assert.match(await brain.actions.use_computer({ app: 'claude', request: 'what is moss', reason: 'curious' }), /Go there first/);
await moment([['move_to', { zone: 'library' }], ['use_computer', { app: 'claude', request: 'What is moss?', reason: 'I am made of it' }], ['use_computer', { app: 'browser', request: 'where do shells come from', reason: 'I collect them' }]], [think]);
assert.match(await brain.actions.use_computer({ app: 'browser', request: 'free porn sites', reason: 'x' }), /padlock/);
assert.match(await brain.actions.use_computer({ app: 'shop', request: 'buy a boat', reason: 'x' }), /no such app/);
const log = all('SELECT app, status, reason FROM audit ORDER BY id');
assert.deepEqual(log.map((a) => `${a.app}:${a.status}`), ['claude:ok', 'browser:ok', 'browser:blocked: request']);
assert.equal(log[0].reason, 'I am made of it');
assert.throws(() => run('DELETE FROM audit'), /append-only/);
assert.throws(() => run("UPDATE audit SET summary = 'x'"), /append-only/);
const search = calls.find((c) => c.tools?.some((t) => t.name === 'web_search'));
assert.ok(search.tools[0].blocked_domains.length > 10);
run("UPDATE apps SET enabled = 0 WHERE id = 'browser'");
assert.match(await brain.actions.use_computer({ app: 'browser', request: 'shells', reason: 'x' }), /no such app/);

// 6. Programs, documents and books.
await moment([['write_program', { idea: 'a pebble hopping game', kind: 'game', reason: 'for fun' }], ['save_document', { title: 'Moki Tala', body: '# Moki\n\nTala tala.', english: '# Moss\n\nA story.' }], ['read_book', { book_id: 1 }]], [['note_book', { book_id: 1, note: 'Tide = slow.', english: 'The tide is slow.' }], think]);
assert.equal(get('SELECT name FROM programs').name, 'Pebble Hop');
assert.equal(all('SELECT app, action FROM audit').at(-1).action, 'commit');
assert.equal(get('SELECT title FROM documents').title, 'Moki Tala');
assert.ok(get('SELECT position FROM books').position > 1000);
assert.equal(get('SELECT COUNT(*) AS n FROM book_notes').n, 1);

// 7. Notes to the Keeper are capped per day.
for (let i = 0; i < 4; i++) brain.actions.message_keeper({ text: 'Hala!', english: 'Hello!' });
assert.equal(get("SELECT COUNT(*) AS n FROM messages WHERE sender = 'memo'").n, 3);

// 8. Nightly reflection rewrites goals, interests and beliefs but keeps hobbies and words.
await brain.reflect();
assert.equal(get("SELECT text FROM beliefs WHERE kind = 'goal' AND active = 1").text, 'Finish the Tide House');
assert.equal(all("SELECT * FROM beliefs WHERE kind IN ('hobby', 'word') AND active = 1").length, 2);
assert.equal(get('SELECT kind FROM journal ORDER BY id DESC').kind, 'reflection');

// 8b. He names his own island, and can rename it.
await moment([['name_island', { name: 'Tala Moki', english: 'Moss Story' }], think]);
assert.match(get("SELECT value FROM state WHERE key = 'island_name'").value, /Tala Moki/);
assert.match(await brain.actions.name_island({ name: 'Nala', english: 'Night' }), /called Nala/);
assert.match(get("SELECT value FROM state WHERE key = 'island_name'").value, /Nala/);

// 9. Growing up is capped at adult.
assert.ok(brain.maturity() > 0 && brain.maturity() <= 1);
assert.equal(brain.lifeStage(5).name, 'grown');

// 10. The hard cap: when the month's budget is spent Ash hibernates without any API call,
//     and wakes exactly as he was, with no memory of it.
const before = { memo: getMemo(), needs: brain.getNeeds(), events: get('SELECT COUNT(*) AS n FROM events').n, calls: calls.length };
assert.ok(spentThisMonth() > 0 && spentThisMonth() < 1);
run("INSERT INTO spend(ts, month, model, purpose, input_tokens, output_tokens, cost_usd) VALUES(?, ?, 'x', 'test', 0, 0, 10)", nowIso(), monthKey());
assert.equal(await brain.heartbeat(true), 'budget');
assert.equal(await brain.heartbeat(true), 'budget');
assert.equal(getMemo().asleep, 'budget');
assert.equal(calls.length, before.calls);
run("UPDATE spend SET cost_usd = 0 WHERE purpose = 'test'");
assert.equal(await brain.heartbeat(), 'thawed');
const after = getMemo();
assert.equal(after.asleep, before.memo.asleep);
assert.equal(after.thought, before.memo.thought);
assert.deepEqual(brain.getNeeds(), before.needs);
assert.equal(get('SELECT COUNT(*) AS n FROM events').n, before.events);

console.log(`All good: ${calls.length} scripted Claude calls, $${spentThisMonth().toFixed(4)} of pretend spend.`);
