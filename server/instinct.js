// Demo mode: with no API key (or MEMO_DEMO=1) Memo runs on these simple instincts instead of
// Claude. It costs nothing and lets you see the island working before you add a key.
import { get } from './db.js';
import { getMemo, getZones } from './world.js';

const pick = (a) => a[Math.floor(Math.random() * a.length)];
const P = (shape, size, position, color, material = 'matte', rotation = [0, 0, 0]) => ({ shape, size, position, rotation, color, material });

const SMALL = [
  (n) => ({ name: n || 'Pebble Stack', animation: 'none', parts: [
    P('sphere', [0.55, 0.3, 0.5], [0, 0.15, 0], '#8d8f86', 'stone'), P('sphere', [0.42, 0.26, 0.4], [0.02, 0.4, 0], '#a3a59b', 'stone'),
    P('sphere', [0.3, 0.2, 0.3], [-0.02, 0.6, 0.01], '#b9b7aa', 'stone'), P('leaf', [0.22, 0.04, 0.12], [0.02, 0.74, 0], '#7fb069', 'moss', [0, 30, 20])] }),
  (n) => ({ name: n || 'Glow Jar', animation: 'pulse', parts: [
    P('cylinder', [0.34, 0.42, 0.34], [0, 0.21, 0], '#cfe8e0', 'glass'), P('cylinder', [0.38, 0.06, 0.38], [0, 0.45, 0], '#8a6b4a', 'wood'),
    P('sphere', [0.14, 0.14, 0.14], [0, 0.22, 0], '#ffe9a3', 'glow'), P('torus', [0.2, 0.02, 0.2], [0, 0.52, 0], '#8a6b4a', 'wood', [0, 0, 90])] }),
  (n) => ({ name: n || 'Wind Spinner', animation: 'spin', parts: [
    P('cylinder', [0.06, 1.1, 0.06], [0, 0.55, 0], '#8a6b4a', 'wood'), P('leaf', [0.5, 0.04, 0.2], [0.25, 1.1, 0], '#e8a87c', 'matte'),
    P('leaf', [0.5, 0.04, 0.2], [-0.25, 1.1, 0], '#f0c987', 'matte'), P('leaf', [0.2, 0.04, 0.5], [0, 1.1, 0.25], '#c38d9e', 'matte'),
    P('leaf', [0.2, 0.04, 0.5], [0, 1.1, -0.25], '#85cdca', 'matte'), P('sphere', [0.1, 0.1, 0.1], [0, 1.12, 0], '#fff3c4', 'glossy')] }),
  (n) => ({ name: n || 'Shell Chime', animation: 'sway', parts: [
    P('cylinder', [0.05, 0.9, 0.05], [-0.3, 0.45, 0], '#8a6b4a', 'wood'), P('cylinder', [0.05, 0.9, 0.05], [0.3, 0.45, 0], '#8a6b4a', 'wood'),
    P('cylinder', [0.7, 0.05, 0.05], [0, 0.9, 0], '#8a6b4a', 'wood'), P('cone', [0.12, 0.16, 0.12], [-0.15, 0.68, 0], '#f6e7d8', 'glossy'),
    P('cone', [0.12, 0.2, 0.12], [0, 0.6, 0], '#f3c5c5', 'glossy'), P('cone', [0.12, 0.14, 0.12], [0.15, 0.7, 0], '#d6e5fa', 'glossy')] }),
];
const BIG = [
  () => ({ name: 'Round House', animation: 'none', supplies: [{ name: 'planks', qty: 4, have: 0 }, { name: 'roof tiles', qty: 3, have: 0 }, { name: 'glass panes', qty: 2, have: 0 }], parts: [
    P('cylinder', [3, 1.7, 3], [0, 0.85, 0], '#e8dcc6', 'matte'), P('cone', [3.7, 1.6, 3.7], [0, 2.5, 0], '#b5654a', 'matte'),
    P('box', [0.7, 1.1, 0.12], [0, 0.55, 1.48], '#7a5236', 'wood'), P('sphere', [0.5, 0.5, 0.1], [0.95, 1.1, 1.2], '#bfe3ee', 'glass'),
    P('sphere', [0.5, 0.5, 0.1], [-0.95, 1.1, 1.2], '#bfe3ee', 'glass'), P('cylinder', [0.35, 0.9, 0.35], [0.8, 3.0, -0.4], '#9a8f84', 'stone'),
    P('sphere', [0.12, 0.12, 0.12], [0.22, 0.55, 1.56], '#e6c35c', 'metal'), P('cylinder', [3.3, 0.14, 3.3], [0, 0.07, 0], '#9a8f84', 'stone')] }),
  () => ({ name: 'Little Bell Tower', animation: 'none', supplies: [{ name: 'stone blocks', qty: 5, have: 0 }, { name: 'a brass bell', qty: 1, have: 0 }], parts: [
    P('box', [1.6, 2.6, 1.6], [0, 1.3, 0], '#b9b3a6', 'stone'), P('box', [1.9, 0.2, 1.9], [0, 2.7, 0], '#8f897d', 'stone'),
    P('cylinder', [0.14, 0.9, 0.14], [0.7, 3.25, 0.7], '#7a5236', 'wood'), P('cylinder', [0.14, 0.9, 0.14], [-0.7, 3.25, 0.7], '#7a5236', 'wood'),
    P('cylinder', [0.14, 0.9, 0.14], [0.7, 3.25, -0.7], '#7a5236', 'wood'), P('cylinder', [0.14, 0.9, 0.14], [-0.7, 3.25, -0.7], '#7a5236', 'wood'),
    P('cone', [2.4, 1.2, 2.4], [0, 4.3, 0], '#4f7a6a', 'matte'), P('cone', [0.5, 0.5, 0.5], [0, 3.3, 0], '#e6c35c', 'metal'),
    P('box', [0.6, 1.0, 0.1], [0, 0.5, 0.82], '#7a5236', 'wood')] }),
];
const PET = (n) => ({ name: pick(['Pip', 'Dot', 'Mossbean', 'Tuft', 'Nib']), animation: 'none', parts: [
  P('sphere', [0.42, 0.34, 0.5], [0, 0.2, 0], pick(['#e9c46a', '#f4a261', '#a8dadc', '#cdb4db', '#f1faee']), 'matte'),
  P('sphere', [0.26, 0.24, 0.26], [0, 0.36, 0.2], '#f6efe0', 'matte'),
  P('sphere', [0.05, 0.06, 0.03], [0.07, 0.4, 0.32], '#22201c', 'glossy'), P('sphere', [0.05, 0.06, 0.03], [-0.07, 0.4, 0.32], '#22201c', 'glossy'),
  P('cone', [0.08, 0.14, 0.08], [0.09, 0.52, 0.18], '#e9a48a', 'matte'), P('cone', [0.08, 0.14, 0.08], [-0.09, 0.52, 0.18], '#e9a48a', 'matte'),
  P('sphere', [0.12, 0.12, 0.12], [0, 0.24, -0.26], '#ffffff', 'matte')] });

export function cannedRecipe(idea, big = false, isPet = false) {
  const base = isPet ? PET() : big ? pick(BIG)() : pick(SMALL)();
  const story = isPet ? `${String(idea).split('.')[0]} came out of the basket and looked at me. I am not alone now.`
    : `I made this because of an idea: ${String(idea).slice(0, 120)}.`;
  return { ...base, story, story_english: story, big };
}

const THOUGHTS = [
  ['Mm. Moki-soft here.', 'Mm. It is moss-soft here.'], ['Where does the sea keep its shells?', 'Where does the sea keep its shells?'],
  ['Tiki, tiki... one more pebble.', 'Little by little... one more pebble.'], ['The light is honey today.', 'The light is the colour of honey today.'],
  ['I should write this down.', 'I should write this down.'], ['Something wants making. I can feel it.', 'Something wants to be made. I can feel it.'],
];
const IDEAS = ['a stack of my favourite pebbles', 'a jar that keeps a bit of evening light', 'something that turns in the wind', 'a chime from shells'];

export async function demoTick(actions) {
  const memo = getMemo(), zones = getZones();
  const gifts = get("SELECT COUNT(*) AS n FROM gifts WHERE status = 'waiting'").n;
  const project = get("SELECT * FROM projects WHERE status = 'planned'");
  const ready = project && JSON.parse(project.supplies).every((s) => s.have >= s.qty);
  const roll = Math.random();
  if (memo.energy < 20) { if (memo.zone !== 'nook') actions.move_to({ zone: 'nook' }); actions.nap({ minutes: 40 }); }
  else if (gifts) { if (memo.zone !== 'board') actions.move_to({ zone: 'board' }); await actions.open_gift({ gift_id: 0 }); }
  else if (ready) { if (memo.zone !== project.zone_id) actions.move_to({ zone: project.zone_id }); actions.build({}); }
  else if (roll < 0.3) actions.move_to({ zone: pick(zones.filter((z) => z.id !== memo.zone)).id });
  else if (roll < 0.6) actions.gather({});
  else if (roll < 0.7) actions.observe({ target: 'the ground nearby' });
  else if (roll < 0.8) await actions.craft({ idea: pick(IDEAS), materials: [] });
  else if (roll < 0.87) actions.write_journal({ title: 'Small things', body: 'Tiki day. I walked and I looked. The island is bigger than my feet think.', english: 'Small things. A little-by-little day. I walked and I looked. The island is bigger than my feet think.', mood: 'content' });
  else if (roll < 0.92) { if (memo.zone !== 'board') actions.move_to({ zone: 'board' }); actions.make_wish({ text: 'A tiny bell, for the wind to ring.', english: 'A tiny bell, for the wind to ring.', reason: 'The island is very quiet.' }); }
  else if (roll < 0.95 && !project) await actions.plan_building({ idea: 'a small round house for rainy days' });
  else actions.observe({ target: 'the sky' });
  const [words, english] = pick(THOUGHTS);
  actions.think({ words, english, mood: pick(['curious', 'content', 'dreamy', 'busy']) });
}

// The little machine that houses a program Memo wrote. Clicking it in the world opens the program.
cannedRecipe.machine = (name, programId) => ({
  name, story: `A machine that runs my program "${name}".`, story_english: `A machine that runs my program "${name}".`,
  animation: 'none', big: false, program_id: programId, parts: [
    P('box', [0.7, 1.0, 0.6], [0, 0.5, 0], '#6b8f71', 'matte'), P('box', [0.76, 0.5, 0.5], [0, 1.2, -0.03], '#587a5f', 'matte'),
    P('box', [0.56, 0.36, 0.04], [0, 1.2, 0.24], '#bff3e0', 'glow'), P('box', [0.6, 0.06, 0.3], [0, 0.98, 0.36], '#d9c7a3', 'wood', [20, 0, 0]),
    P('sphere', [0.08, 0.08, 0.08], [-0.15, 1.02, 0.4], '#e76f51', 'glossy'), P('sphere', [0.08, 0.08, 0.08], [0.12, 1.02, 0.4], '#f4d35e', 'glossy'),
    P('leaf', [0.3, 0.04, 0.14], [0.2, 1.5, 0], '#7fb069', 'moss', [0, 20, 30])],
});
