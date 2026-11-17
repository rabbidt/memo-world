import { sunTimes, moon, season, clockTime } from './almanac.js';
import { api, key } from './api.js';
import { marked } from '/vendor/marked.js';
import DOMPurify from '/vendor/purify.js';

// Ash's documents are Markdown. They are rendered with marked and cleaned with DOMPurify.
const markdown = (text) => { const d = document.createElement('div'); d.className = 'doc'; d.innerHTML = DOMPurify.sanitize(marked.parse(String(text || ''), { breaks: true }), { FORBID_TAGS: ['img', 'style', 'form', 'input', 'iframe', 'video', 'audio'], FORBID_ATTR: ['style'] }); for (const a of d.querySelectorAll('a')) { a.target = '_blank'; a.rel = 'noopener noreferrer'; } return d; };

// Tiny DOM helper. Everything Ash or a visitor wrote goes in as text, never as HTML.
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === 'class') el.className = v; else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (k === 'style') el.style.cssText = v; else if (k in el && k !== 'list') el[k] = v; else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
  return el;
}
const $ = (id) => document.getElementById(id);
const when = (ts) => {
  const d = new Date(ts), mins = Math.round((Date.now() - d) / 60000);
  if (mins < 1) return 'just now'; if (mins < 60) return `${mins} min ago`;
  if (mins < 60 * 20) return `${Math.round(mins / 60)} h ago`;
  return d.toLocaleString([], { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};
// Ash's own words, with the English underneath when it differs.
const said = (words, english, cls = 'words') => [h('div', { class: cls }, words),
  english && english.trim() !== String(words).trim() ? h('div', { class: 'english' }, english) : null];
let toastTimer;
function toast(msg) { const t = $('toast'); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => { t.hidden = true; }, 3200); }
async function act(fn, ok) { try { await fn(); if (ok) toast(ok); return true; } catch (e) { toast(e.message); return false; } }

const ACTIVITY = { idle: 'pottering about', walking: 'walking', looking: 'looking closely at something', gathering: 'gathering', crafting: 'making something',
  writing: 'writing in his notebook', napping: 'napping', sleeping: 'asleep', computing: 'at his computer', playing: 'playing' };
const FEEL = (v) => (v < 25 ? 'not at all' : v < 50 ? 'a little' : v < 75 ? 'quite' : 'very');

export async function initUI({ world, data, focusOn, setFollow, refreshBoard }) {
  const me = await api('me');
  const isOwner = me.role === 'owner';
  const S = { island: data.island, areas: data.areas || [], memo: data.memo, inventory: data.inventory, project: data.project, programs: data.programs, parcels: data.parcels,
    budget: data.budget, status: data.status, wishes: [], journal: [], events: [], mind: [], messages: [], audit: [], invites: [], documents: [], books: { books: [], notes: [] }, apps: [], tab: 'now', unread: new Set() };

  const TABS = [['now', 'Now'], ['journal', 'Journal'], ['wishes', 'Wishes'], ['mind', 'Mind'], ['town', 'Town'], ['library', 'Library'],
    ...(isOwner ? [['notes', 'Notes'], ['computer', 'Computer'], ['keeper', 'Keeper']] : [])];
  const zoneName = (id) => world.zones.find((z) => z.id === id)?.name || id;

  function drawTabs() {
    $('tabs').replaceChildren(...TABS.map(([id, label]) => h('button', { class: S.tab === id ? 'on' : '', onclick: () => { S.tab = id; S.unread.delete(id); drawTabs(); draw(); } },
      label, S.unread.has(id) ? h('span', { class: 'dot' }) : null)));
  }

  // ----- tabs -----
  const views = {
    now() {
      const m = S.memo, n = m.needs || {};
      const sleeping = m.asleep === 'budget' ? 'hibernating until the budget renews' : m.asleep ? 'asleep in his nook' : null;
      return [
        !S.status.brain.ok && isOwner ? h('div', { class: 'banner bad' }, S.status.brain.message) : null,
        S.status.demo ? h('div', { class: 'banner' }, isOwner ? 'Demo mode: Ash is running on simple instincts. Add your API key to the .env file and restart to wake his real mind.' : 'Ash is in demo mode right now.') : null,
        h('div', { class: 'who' }, h('div', { class: 'avatar' }, h('i'), h('i'), h('b')),
          h('div', {}, h('h2', {}, 'Ash'), h('div', { class: 'muted' }, `${sleeping || ACTIVITY[m.activity] || m.activity} · ${zoneName(m.zone)}`),
            h('div', { class: 'chips', style: 'margin-top:5px' }, h('span', { class: 'chip' }, m.stage), h('span', { class: 'chip' }, `feeling ${m.mood}`)))),
        h('div', { class: 'thought' }, said(m.thought, m.thoughtEnglish)),
        skyChips(),
        h('h3', {}, 'How he feels'),
        h('div', { class: 'bars' },
          ...[['Energy', m.energy, '', `${m.energy}`], ['Lonely', n.loneliness, 'rose', FEEL(n.loneliness)], ['Curious', n.curiosity, 'blue', FEEL(n.curiosity)], ['Wants to make', n.urge, 'warm', FEEL(n.urge)], ['Grown up', Math.round(m.maturity * 100), '', m.stage]]
            .flatMap(([label, v, cls, txt]) => [h('span', {}, label), h('div', { class: `bar ${cls}` }, h('i', { style: `width:${v || 0}%` })), h('span', { class: 'muted' }, txt)])),
        h('h3', {}, 'In his pouch'),
        S.inventory.length ? h('div', { class: 'chips' }, S.inventory.map((i) => h('span', { class: 'chip', title: i.note || '' }, `${i.name} ×${i.qty}${i.source === 'gift' ? ' 🎁' : ''}`))) : h('div', { class: 'muted' }, 'Empty for now.'),
        h('h3', {}, 'Lately'),
        h('ul', { class: 'feed' }, S.events.slice(0, 25).map((e) => h('li', {}, h('time', {}, when(e.ts)), e.summary))),
      ];
    },
    journal() {
      if (!S.journal.length) return [h('p', { class: 'muted' }, 'Ash has not written anything yet. He will.')];
      return S.journal.map((j) => h('div', { class: `entry ${j.kind === 'reflection' ? 'reflection' : ''}` },
        h('div', { class: 'small muted' }, `${when(j.ts)}${j.kind === 'reflection' ? ' · night reflection' : ''}${j.mood ? ` · ${j.mood}` : ''}`),
        h('h4', {}, j.title), h('div', { class: 'body' }, j.body), j.english && j.english.trim() !== `${j.title}. ${j.body}`.trim() && j.english.trim() !== j.body.trim() ? h('div', { class: 'english' }, j.english) : null));
    },
    wishes() {
      const open = S.wishes.filter((w) => w.status === 'open'), past = S.wishes.filter((w) => w.status !== 'open');
      return [
        h('p', { class: 'muted' }, 'Ash pins wishes to the notice board. Grant one by leaving a gift; it appears as a parcel for him to find and open.'),
        open.length ? null : h('p', {}, 'No open wishes right now.'),
        ...open.map((w) => wishCard(w)),
        h('h3', {}, 'Leave a gift, just because'), giftForm(null),
        past.length ? h('h3', {}, 'Answered') : null,
        ...past.slice(0, 15).map((w) => h('div', { class: 'note done' }, said(w.text, w.english), h('div', { class: 'small muted' }, `${w.status}${w.reply ? ` · “${w.reply}”` : ''} · ${when(w.answered_at || w.ts)}`))),
      ];
    },
    mind() {
      const group = (kind, title, empty) => { const rows = S.mind.filter((b) => b.kind === kind);
        return [h('h3', {}, title), rows.length ? h('ul', { class: 'feed' }, rows.map((b) => h('li', {}, b.text))) : h('div', { class: 'muted' }, empty)]; };
      return [h('p', { class: 'muted' }, 'Nobody sets these but Ash. He changes them as he lives, and rethinks them every night.'),
        ...group('goal', 'Goals', 'No goals yet.'), ...group('interest', 'Interests', 'Nothing in particular yet.'), ...group('hobby', 'Hobbies', 'No hobbies yet.'),
        ...group('belief', 'Beliefs', 'Still working the world out.'), ...group('word', "Words of Ash's own", 'He has not invented any words yet.')];
    },
    town() {
      const made = [...world.objects.values()].map((g) => g.userData.obj).filter((o) => o.kind === 'creation' || o.kind === 'pet').reverse();
      const p = S.project;
      return [
        h('h3', { style: 'margin-top:0' }, 'Building in progress'),
        p ? h('div', { class: 'entry' }, h('h4', {}, p.name), h('div', { class: 'small muted' }, `At the ${zoneName(p.zone_id)}`),
          h('div', { class: 'chips', style: 'margin-top:8px' }, p.supplies.map((s) => h('span', { class: 'chip' }, `${s.name} ${s.have}/${s.qty}`))),
          h('div', { class: 'small muted', style: 'margin-top:6px' }, 'Send supplies from the Wishes tab.')) : h('div', { class: 'muted' }, 'Nothing staked out. Ash plans big builds when he feels like it.'),
        h('h3', {}, 'Beyond the island'),
        S.areas.length ? S.areas.map((a) => h('div', { class: 'item' }, h('div', {}, h('strong', {}, a.name), h('div', { class: 'small muted' }, `${a.status === 'open' ? 'Open to Ash' : 'Promised, not built yet'}${a.description ? ` · ${a.description}` : ''}`))))
          : h('div', { class: 'muted' }, 'Nowhere yet. New places open when Ash wishes to travel and you agree.'),
        h('h3', {}, 'Programs he invented'),
        S.programs.length ? S.programs.map((g) => h('div', { class: 'item' }, h('div', {}, h('strong', {}, g.name), h('div', { class: 'small muted' }, `${g.kind} · used ${g.plays} times`), h('div', { class: 'small' }, g.english || g.description)),
          h('button', { class: 'primary', onclick: () => openProgram(g) }, g.kind === 'game' ? 'Play' : 'Open'))) : h('div', { class: 'muted' }, 'None yet.'),
        h('h3', {}, `Things in the world because of Ash (${made.length})`),
        made.length ? made.map((o) => h('div', { class: 'item' }, h('div', {}, h('strong', {}, o.name), h('div', { class: 'small muted' }, `${o.kind === 'pet' ? 'pet' : o.params.big ? 'building' : 'made'} · ${zoneName(o.zone_id)} · ${when(o.created_at)}`)),
          h('button', { onclick: () => { focusOn(o.x, o.z, o.params.big ? 18 : 9); select(o); } }, 'Show'))) : h('div', { class: 'muted' }, 'Nothing yet. Give him time.'),
      ];
    },
    library() {
      const open = S.documents.find((d) => d.id === S.openDoc);
      if (open) return [h('button', { onclick: () => { S.openDoc = null; draw(); } }, '← All writing'),
        h('div', { class: 'entry', style: 'margin-top:10px' }, h('div', { class: 'small muted' }, `Written ${when(open.ts)}${open.updated_at !== open.ts ? ` · rewritten ${when(open.updated_at)}` : ''}`), h('h4', {}, open.title), markdown(open.body)),
        open.english ? h('div', { class: 'entry' }, h('h3', { style: 'margin-top:0' }, 'In English'), markdown(open.english)) : null];
      const B = S.books;
      return [
        h('h3', { style: 'margin-top:0' }, "Ash's own writing"),
        S.documents.length ? S.documents.map((d) => h('div', { class: 'item' }, h('div', {}, h('strong', {}, d.title), h('div', { class: 'small muted' }, `${when(d.updated_at)} · ${d.body.split(/\s+/).length} words`)),
          h('button', { onclick: () => { S.openDoc = d.id; draw(); } }, 'Read'))) : h('div', { class: 'muted' }, 'When he feels inspired, Ash writes longer pieces in his text editor. Nothing yet.'),
        ...(isOwner ? [
          h('h3', {}, 'Books on his shelves'),
          h('p', { class: 'small muted' }, `Put .epub, .txt or .md files in this folder on the computer running the island, and Ash will find them: ${B.folder || ''}. Only you can see this list, and the books never leave that computer except for the few pages he is reading.`),
          B.books.length ? B.books.map((b) => h('div', { class: 'item' }, h('div', { style: 'flex:1' }, h('strong', {}, b.title), h('div', { class: 'bar', style: 'margin-top:5px' }, h('i', { style: `width:${Math.round((b.position / b.chars) * 100)}%` })),
            h('div', { class: 'small muted' }, b.finished_at ? `Finished ${when(b.finished_at)}` : b.started_at ? `${Math.round((b.position / b.chars) * 100)}% read` : 'Not opened yet')))) : h('div', { class: 'muted' }, 'The shelves are empty.'),
          h('button', { style: 'margin-top:8px', onclick: async () => { await act(() => api('books/scan', {}), 'Shelves checked.'); load('books'); } }, 'Check the folder for new books'),
          B.notes.length ? h('h3', {}, 'His margin notes') : null,
          ...B.notes.map((n) => h('div', { class: 'note' }, h('div', { class: 'small muted' }, `${n.title} · ${when(n.ts)}`), said(n.note, n.english))),
        ] : []),
      ];
    },
    notes() {
      const input = h('textarea', { placeholder: 'Write Ash a note…', maxLength: 400 });
      return [h('p', { class: 'muted' }, `Ash may send you up to three notes a day, in your daytime only. He reads your replies the next time he looks up.`),
        h('div', { class: 'stack' }, input, h('button', { class: 'primary', onclick: async () => { if (await act(() => api('messages', { text: input.value }), 'Note sent.')) { input.value = ''; load('messages'); } } }, 'Send note')),
        h('h3', {}, 'Notes'),
        S.messages.length ? S.messages.map((m) => h('div', { class: `bubble-msg ${m.sender}` }, h('div', { class: 'small muted' }, `${m.sender === 'memo' ? 'Ash' : 'You'} · ${when(m.ts)}`), said(m.text, m.english, ''))) : h('div', { class: 'muted' }, 'No notes yet.')];
    },
    computer() {
      const q = h('input', { placeholder: 'Search the audit…', value: S.auditQ || '', onchange: (e) => { S.auditQ = e.target.value; load('audit'); } });
      const app = h('select', { onchange: (e) => { S.auditApp = e.target.value; load('audit'); } }, ['', 'claude', 'wikipedia', 'browser', 'github'].map((a) => h('option', { value: a, selected: (S.auditApp || '') === a }, a || 'All apps')));
      return [h('p', { class: 'muted' }, "Every search, page, question to Claude, blocked attempt and GitHub commit on Ash's computer is recorded here with his reason. The record cannot be changed or erased, by him or anyone."),
        h('div', { class: 'row' }, q, app),
        h('table', { class: 'audit', style: 'margin-top:8px' }, S.audit.map((a) => h('tr', {}, h('td', { style: 'width:74px' }, h('div', { class: 'small muted' }, when(a.ts)), h('span', { class: `tag ${a.status.startsWith('blocked') ? 'blocked' : ''}` }, a.app)),
          h('td', {}, h('strong', {}, a.query), a.reason ? h('div', { class: 'small muted' }, `Why: ${a.reason}`) : null, h('div', { class: 'small' }, a.status === 'ok' ? a.summary : `${a.status}${a.summary ? ` · ${a.summary}` : ''}`),
            ...(a.sources || []).slice(0, 4).map((s) => h('div', { class: 'small' }, h('a', { href: s.url, target: '_blank', rel: 'noopener noreferrer' }, s.title || s.url))))))),
        S.audit.length ? null : h('p', { class: 'muted' }, 'Nothing recorded.')];
    },
    keeper() {
      const b = S.budget || { spent: 0, cap: 10, byPurpose: [] };
      const label = h('input', { placeholder: "Visitor's name, e.g. Sam", maxLength: 30 });
      const link = (t) => `${location.origin}/?k=${t}`;
      return [
        h('h3', { style: 'margin-top:0' }, `Budget for ${b.month || 'this month'}`),
        h('div', { class: 'meter' }, h('i', { style: `width:${Math.min(100, (b.spent / b.cap) * 100)}%` })),
        h('div', { class: 'small', style: 'margin-top:4px' }, `$${b.spent.toFixed(3)} of $${b.cap.toFixed(2)} used. When it runs out Ash hibernates, and wakes next month as if no time had passed.`),
        b.byPurpose.length ? h('div', { class: 'chips', style: 'margin-top:6px' }, b.byPurpose.map((p) => h('span', { class: 'chip' }, `${p.purpose}: ${p.calls} · $${p.cost.toFixed(3)}`))) : null,
        h('h3', {}, "Apps on Ash's computer"),
        h('p', { class: 'small muted' }, 'Only you can switch these. If Ash wants a new app he will pin a wish for it; new apps need adding to the code before they can be switched on.'),
        ...S.apps.map((a) => h('label', { class: 'item' }, h('div', {}, h('strong', {}, a.name), h('div', { class: 'small muted' }, a.description)),
          h('input', { type: 'checkbox', style: 'width:auto', checked: Boolean(a.enabled), onchange: async (e) => { await act(async () => { S.apps = await api(`apps/${a.id}`, { enabled: e.target.checked }); }, `${a.name} ${e.target.checked ? 'on' : 'off'}.`); } }))),
        h('h3', {}, 'Visitor links'),
        h('p', { class: 'small muted' }, 'Visitors can watch, read the journal and leave up to three gentle gifts a day. They cannot see your notes, the audit or the budget.'),
        h('div', { class: 'row' }, label, h('button', { class: 'primary', onclick: async () => { if (await act(() => api('invites', { label: label.value }), 'Link created.')) load('invites'); } }, 'Create link')),
        ...S.invites.map((i) => h('div', { class: 'item' }, h('div', { style: 'min-width:0' }, h('strong', {}, i.label), i.revoked ? h('span', { class: 'tag blocked', style: 'margin-left:6px' }, 'revoked') : h('code', { class: 'link' }, link(i.token))),
          i.revoked ? null : h('div', { class: 'row', style: 'flex:none' }, h('button', { onclick: () => navigator.clipboard?.writeText(link(i.token)).then(() => toast('Copied.')) }, 'Copy'), h('button', { onclick: async () => { if (await act(() => api(`invites/${i.token}/revoke`, {}), 'Revoked.')) load('invites'); } }, 'Revoke')))),
        h('h3', {}, 'Nudge'),
        h('button', { onclick: () => act(async () => { const r = await api('poke', {}); toast(`Ash: ${r.result}`); }) }, 'Let Ash take a moment now'),
        h('div', { class: 'small muted', style: 'margin-top:6px' }, `He thinks on his own every ${S.status.tickMinutes} minutes while awake. Renderer: ${document.body.dataset.backend || ''}.`),
      ];
    },
  };

  // The real sky over London today, which is also the island's sky.
  function skyChips() {
    const d = new Date(), t = sunTimes(d), s = season(d);
    return h('div', { class: 'chips', style: 'margin-top:8px' }, [s.label, `sunrise ${clockTime(t.sunrise)}`, `sunset ${clockTime(t.sunset)}`, moon(d).name, s.snow ? 'snow today' : null]
      .filter(Boolean).map((x) => h('span', { class: 'chip' }, x)));
  }
  function wishCard(w) {
    const supply = Boolean(w.project_id);
    if (w.kind === 'travel') return h('div', { class: 'note' }, said(w.text, w.english), w.reason ? h('div', { class: 'small muted', style: 'margin:4px 0 8px' }, w.reason) : null, isOwner ? travelForm(w) : h('div', { class: 'small muted' }, 'A wish to travel. Only the Keeper can answer it.'));
    return h('div', { class: 'note' }, said(w.text, w.english), w.reason ? h('div', { class: 'small muted', style: 'margin:4px 0 8px' }, w.reason) : null,
      supply ? h('div', { class: 'row' }, h('span', { class: 'small muted' }, 'Supplies for his building.'),
        h('button', { class: 'primary', onclick: () => send({ wish_id: w.id, note: '' }) }, 'Send supplies')) : giftForm(w));
  }
  function travelForm(w) {
    const name = h('input', { placeholder: 'Name the new place, e.g. Orchard Isle', maxLength: 60 });
    const desc = h('input', { placeholder: 'What is it like? (optional)', maxLength: 300 });
    return h('div', { class: 'stack' }, h('div', { class: 'small muted' }, 'Ash wants to travel. Promise him a new place and it is recorded for building; he is told it will open in time.'), name, desc, h('div', { class: 'row' },
      h('button', { class: 'primary', onclick: async () => { if (await act(() => api(`wishes/${w.id}/promise-area`, { name: name.value, description: desc.value }), 'Promised. Ash will hear of it.')) load('wishes'); } }, 'Promise this place'),
      h('button', { onclick: async () => { if (await act(() => api(`wishes/${w.id}/decline`, { note: '' }), 'Answered: not this time.')) load('wishes'); } }, 'Not this time')));
  }
  function giftForm(w) {
    const name = h('input', { placeholder: w ? 'What are you giving?' : 'A gift, e.g. a tiny bell', maxLength: 60 });
    const note = h('input', { placeholder: 'A short note (optional)', maxLength: 200 });
    const kind = isOwner ? h('select', {}, [['item', 'Something for his pouch'], ['special', 'A special object for the world'], ['pet', 'A pet']].map(([v, t]) => h('option', { value: v }, t))) : null;
    const desc = isOwner ? h('input', { placeholder: 'Describe how it looks (for objects and pets)', maxLength: 300, hidden: true }) : null;
    if (kind) kind.onchange = () => { desc.hidden = kind.value === 'item'; };
    return h('div', { class: 'stack' }, name, kind, desc, note, h('div', { class: 'row' },
      h('button', { class: 'primary', onclick: async () => { if (await send({ wish_id: w?.id, name: name.value, note: note.value, kind: kind?.value, description: desc?.value })) { name.value = note.value = ''; } } }, w ? 'Grant this wish' : 'Leave gift'),
      w && isOwner ? h('button', { onclick: async () => { if (await act(() => api(`wishes/${w.id}/decline`, { note: note.value }), 'Answered: not this time.')) load('wishes'); } }, 'Not this time') : null));
  }
  const send = (body) => act(() => api('gifts', body), 'Left by the notice board.').then((ok) => { if (ok) { load('wishes'); load('world'); } return ok; });

  function draw() { const body = $('tab-body'), y = body.scrollTop; body.replaceChildren(...(views[S.tab]() || []).flat().filter(Boolean)); body.scrollTop = y; }

  // ----- selection card and program player -----
  function select(o) {
    const card = $('card');
    if (!o) { card.hidden = true; return; }
    const close = h('button', { class: 'quiet x', onclick: () => { card.hidden = true; } }, '✕');
    if (o.memo) card.replaceChildren(close, h('h2', {}, 'Ash'), h('div', { class: 'muted small' }, `${S.memo.stage} · feeling ${S.memo.mood}`), h('div', { class: 'story' }, said(S.memo.thought, S.memo.thoughtEnglish, '')));
    else {
      const prog = o.params?.program_id ? S.programs.find((p) => p.id === o.params.program_id) : null;
      const zone = world.zones.find((z) => z.id === o.zone_id && ['notice_board', 'burrow', 'workshop_hut', 'library_tower', 'pond'].includes(o.kind));
      card.replaceChildren(close, h('h2', {}, o.name || o.kind),
        h('div', { class: 'muted small' }, o.kind === 'pet' ? `Ash's pet · arrived ${when(o.created_at)}` : o.kind === 'creation' ? `${o.created_by === 'memo' ? 'Made by Ash' : `A gift from ${o.created_by}`} · ${when(o.created_at)}` : o.kind === 'build_site' ? 'Staked out by Ash, waiting for supplies' : 'Part of the island'),
        h('div', { class: 'story' }, o.params?.story ? said(o.params.story, o.params.story_english, '') : zone?.description || ''),
        prog ? h('button', { class: 'primary', style: 'margin-top:10px', onclick: () => openProgram(prog) }, prog.kind === 'game' ? 'Play' : 'Open') : null);
    }
    card.hidden = false;
  }
  function openProgram(p) {
    $('modal-title').textContent = p.name;
    // Ash's code runs only inside this locked frame: no network, no access to this page.
    $('modal-body').replaceChildren(h('iframe', { src: `/api/programs/${p.id}/run?k=${encodeURIComponent(key)}`, sandbox: 'allow-scripts', referrerPolicy: 'no-referrer', title: p.name }));
    $('modal').hidden = false;
    api(`programs/${p.id}/played`, {}).catch(() => {});
  }
  $('modal-close').onclick = () => { $('modal').hidden = true; $('modal-body').replaceChildren(); };

  // ----- data -----
  const loaders = {
    world: async () => { const d = await api('world'); Object.assign(S, { memo: d.memo, inventory: d.inventory, project: d.project, programs: d.programs, parcels: d.parcels, budget: d.budget, status: d.status, island: d.island, areas: d.areas || [] }); title(); refreshBoard(S.wishes, S.parcels); },
    wishes: async () => { S.wishes = await api('wishes'); refreshBoard(S.wishes, S.parcels); },
    journal: async () => { S.journal = await api('journal'); },
    events: async () => { S.events = await api('events'); },
    mind: async () => { S.mind = await api('mind'); },
    messages: async () => { if (isOwner) S.messages = await api('messages'); },
    audit: async () => { if (isOwner) S.audit = await api(`audit?q=${encodeURIComponent(S.auditQ || '')}&app=${S.auditApp || ''}`); },
    invites: async () => { if (isOwner) S.invites = await api('invites'); },
    documents: async () => { S.documents = await api('documents'); },
    books: async () => { if (isOwner) S.books = await api('books'); },
    apps: async () => { if (isOwner) S.apps = await api('apps'); },
  };
  const pending = new Set();
  async function load(what) { if (pending.has(what)) return; pending.add(what); try { await loaders[what](); } catch (e) { console.warn(e); } pending.delete(what); draw(); }
  await Promise.all(Object.keys(loaders).map((k) => loaders[k]().catch((e) => console.warn(e))));

  function bubble() {
    const b = $('bubble'), m = S.memo;
    b.querySelector('.words').textContent = m.thought || '';
    const e = b.querySelector('.english');
    e.textContent = m.thoughtEnglish || ''; e.style.display = m.thoughtEnglish && m.thoughtEnglish !== m.thought ? '' : 'none';
    b.dataset.has = m.thought ? '1' : '';
  }
  function title() {
    const i = S.island || {}, name = i.name || "Ash's Island";
    const h = $('island-name'); h.textContent = name; h.title = i.english && i.english !== i.name ? i.english : '';
    document.title = i.name ? `${i.name} · Ash's island` : name;
  }
  function clock() {
    title();
    const d = new Date();
    $('clock').textContent = `${d.toLocaleDateString([], { weekday: 'long' })} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} · ${isOwner ? 'You are the Keeper' : `Visiting as ${me.label}`}`;
    const hr = new URLSearchParams(location.search).get('hour') ?? d.getHours();
    document.body.classList.toggle('night', hr < 6 || hr >= 20);
  }
  setInterval(clock, 20000); clock(); bubble(); drawTabs(); draw();

  // ----- buttons -----
  let following = false;
  $('btn-follow').onclick = (e) => { following = !following; setFollow(following); e.target.classList.toggle('on', following); };
  $('btn-find').onclick = () => focusOn(world.memo.root.position.x, world.memo.root.position.z, 10);
  $('btn-english').onclick = (e) => { e.target.classList.toggle('on'); document.body.classList.toggle('no-english'); };
  $('btn-panel').onclick = () => document.body.classList.toggle('panel-hidden');
  if (innerWidth < 760) document.body.classList.add('panel-hidden');

  const MAP = { journal: ['journal'], wishes: ['wishes'], gifts: ['world'], inventory: ['world'], mind: ['mind'], projects: ['world'], programs: ['world'], messages: ['messages'], web: ['audit'], documents: ['documents'], books: ['books'], budget: ['world'], status: ['world'], event: ['events'], objects: [] };
  const TAB_OF = { journal: 'journal', wishes: 'wishes', messages: 'notes', mind: 'mind', programs: 'town', projects: 'town', web: 'computer', documents: 'library' };
  return {
    select,
    memo(m) { S.memo = m; bubble(); if (S.tab === 'now') draw(); },
    changed(type) {
      for (const what of MAP[type] || []) load(what);
      const tab = TAB_OF[type];
      if (tab && tab !== S.tab && TABS.some(([id]) => id === tab)) { S.unread.add(tab); drawTabs(); }
      if (type === 'objects' && S.tab === 'town') draw();
    },
  };
}
