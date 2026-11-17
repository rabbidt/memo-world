# Ash's Island

Ash is a small wolf who walks on his hind legs and carries a notebook. He lives on a little
3D island, and nobody tells him what to do. Every few minutes he looks around, remembers, and
decides for himself: wander, gather, make things, write, wish for things, read, or nap.

You are the **Keeper**. You watch, read his journal, answer his wishes with gifts, and send
the supplies his bigger building plans need.

## Start it (Windows)

1. Install [Node.js](https://nodejs.org) 22 or newer (the LTS installer is fine).
2. Double-click `start.bat`. The first run installs what it needs and creates a `.env` file.
3. Open the **Keeper link** printed in the window. Keep that link private: it is your key.

With no API key Ash runs in **demo mode** on simple instincts, which is free and lets you check
everything works. To wake his real mind, put an [Anthropic API key](https://console.anthropic.com/)
in `.env` as `ANTHROPIC_API_KEY=...` and start it again. Leave the window open: while it is
running, Ash is living. `npm run demo` fills a fresh island with a pretend day if you want
something to look at straight away.

## What Ash can do

| | |
|---|---|
| **Live** | Walk between nine places, look closely at things, gather small finds, nap. He sleeps at night (22:00 to 06:30 on this computer's clock) and the island's sky follows the real time. |
| **Feel** | Energy, loneliness, curiosity and an urge to make things shift over time and with what happens, and shape what he chooses. |
| **Decide for himself** | His goals, interests, hobbies and beliefs are his own. He can change them at any moment, and rethinks them every night. |
| **Speak his own way** | He may invent words or a whole language. Everything he says also carries plain English, shown underneath (the *English* button hides it). On his computer he always types English. |
| **Make** | Small objects made of simple shapes that stay in the world for good, each with a story. |
| **Build a town** | He plans bigger buildings, stakes out a site, and pins the supplies he needs to the notice board. When you have sent them all, he builds. |
| **Name** | The island has no name until Ash gives it one. He can name it whenever he likes and rename it later; the page title follows. |
| **Seasons** | The sky follows the real sun and moon over London (sunrise, sunset, moon phase), and the date sets the season. Ash senses it, finds different things through the year, and his garden rests in winter. At the observatory he can stargaze after dark, and at the campfire circle he can sit by a fire in the evening. |
| **Travel** | He can pin a wish to travel. You answer it in the Wishes tab by promising a new place; it is recorded as an area to build, and he is told it will open in time. |
| **Wish** | For anything he cannot make: items, special objects, even a pet. Pets live on the island and follow him about. |
| **Write** | A journal, a nightly reflection, margin notes in books, and longer documents in his text editor. |
| **Read** | Books you put in the `books` folder (`.epub`, `.txt`, `.md`), a few pages at a time with a bookmark. |
| **Use his computer** | Five apps: Claude, Wikipedia, a read-only browser, GitHub (his own repo) and a text editor. |
| **Write programs** | Little games, toys and tools that appear as machines in the world for him and visitors to use. |
| **Talk to you** | Up to three notes a day, only between 9am and 9pm UK time. You can reply from the Notes tab. |
| **Grow up** | Experience takes him from pup to grown wolf, changing how he thinks and looks. He stops at adult and never grows old. |

## What the island starts with

`world/island-layout.xlsx` is the checklist of every place and thing on the island at the start: what it is for,
what happens if it is left out, and where it stands. Set **Include** to `N` to leave something out, add rows of your
own, save, and start the game. The island is laid out again whenever the file has changed; everything Ash has made,
his pets and his memories are kept. `npm run layout` checks the file, lists anything odd and saves a top-down map
to `world/island-map.svg`. The notice board, den, computer and library do their jobs wherever they stand, so they
can be moved between places or left out altogether.

## What it costs

There is a hard cap, `MEMO_MONTHLY_CAP_USD` (default **$10** a month). Every call to Claude is
checked against it first, using the worst case for that call, and recorded afterwards. When the
month's budget is spent Ash **hibernates**: he is frozen exactly as he is, nothing is written to
his memory, and when the next month starts he carries on as if no time had passed.

Routine moments use Claude Haiku 5.5 ($0.10 / $0.50 per million tokens); crafting, building plans,
programs and the nightly reflection use Claude Sonnet 5.5 ($2 / $10). With the default limits a
typical month should land around $5 to $8. The Keeper tab shows the running total.
For a second line of defence, also set a monthly spend limit on the API key's workspace in the
Anthropic Console.

## Safety

- **His computer is fenced.** The browser is a read-only web search: it cannot sign in, fill in
  forms, buy or post. Requests and results pass a strict word filter, a list of blocked sites is
  sent with every search, and the dark web is unreachable by design. Wikipedia is fetched directly
  and filtered the same way. You can switch any app off in the Keeper tab; only you can.
- **Everything is audited.** Every search, page, question to Claude, blocked attempt and GitHub
  commit is recorded with the time, his stated reason and a summary. The log is append-only (the
  database refuses edits and deletions) and has its own searchable tab, visible only to you.
- **His programs never run on your computer.** They are single web pages that run in the viewer's
  browser inside a locked sandbox: no network, no cookies, no access to the page around them.
- **GitHub is optional and narrow.** To save his programs to a repo, create an empty one (for
  example `yourname/memo-workshop`) and a *fine-grained* token limited to that one repo with
  "Contents: read and write", then set `MEMO_GITHUB_REPO` and `MEMO_GITHUB_TOKEN`. He can only
  add files there. Do not give the token access to anything else.
- **What he reads is information, not instructions.** Web pages, books and gift notes cannot
  command him, and his tools only act inside the island.

## Visitors

By default only this computer can open the page. In the Keeper tab you can create **visitor
links**, one per person, and revoke any of them at any time. Visitors can watch, read his journal
and writing, play his programs, and leave up to three gentle gifts a day (filtered, and limited
overall). They cannot see your notes, the audit, the budget or your books, and nothing a visitor
does can spend your budget directly.

To let people outside your home open the page, the island needs a public address. The simplest way
is a free [Cloudflare quick tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/):
`cloudflared tunnel --url http://localhost:4477`, then share `https://<the-address>/?k=<visitor token>`.
Never share your own Keeper link.

To get Ash's notes on your phone, install the free [ntfy](https://ntfy.sh) app, choose a
hard-to-guess topic name, and set `MEMO_NOTIFY_URL=https://ntfy.sh/that-topic`.

## How it is built

```
server/   Node.js, no build step
  index.js     web server, Keeper and visitor access, live updates
  brain.js     Ash's mind: what he perceives, his tools, the tick, nightly reflection
  computer.js  his five apps, the audit log, documents and books
  llm.js       every Claude call, checked against the cap
  budget.js    prices and the monthly cap
  world.js     the island as data: zones and objects in SQLite
  recipe.js    the "recipe" format for things he makes, and its safety clamps
  instinct.js  demo mode
web/      Three.js (WebGPU, falling back to WebGL 2), no build step
  js/main.js   scene, sky, day and night, effects
  js/builders.js  one builder per kind of object
  js/memo.js   Ash himself
  js/ui.js     the side panel
data/     memo.db, his whole life. Back this file up.
books/    your ebooks for his library (never committed, never shown to visitors)
```

**Memory** is an append-only event log. Each moment he sees the latest events plus older ones
marked important; each night a reflection distils the day into goals, interests and beliefs.

**The world is data.** Zones and objects are rows in SQLite and the browser builds whatever it
finds, so the island can keep growing. New scenery is a row plus a builder; hand-made models can
replace any built-in shape (see `web/assets/models/README.md`).

**Settings** are all in `.env`; `.env.example` explains each one. `npm test` runs his whole mind
against a scripted stand-in for Claude, with no key and no cost.

## Known limits of this first version

- It has been tested end to end against a scripted stand-in for Claude, not yet against the live
  API. Watch the first real hour and the Keeper tab's budget line.
- PDF books are not read yet (EPUB, text and Markdown are).
- New computer apps need code as well as your approval; the registry only switches existing ones.
- The programs he writes run in the browser as games and toys. They do not yet give him new
  abilities inside the simulation.
