// A plain word filter used on three things: what Memo asks its computer, what the computer
// brings back, and what visitors write. It is deliberately strict; false alarms are fine here.
const BLOCKED_WORDS = [
  'porn', 'porno', 'xxx', 'nsfw', 'nude', 'nudes', 'naked', 'sex', 'sexy', 'sexual', 'erotic', 'erotica', 'hentai',
  'fetish', 'escort', 'onlyfans', 'camgirl', 'stripper', 'incest', 'rape', 'molest', 'pedo', 'pedophile', 'lolita',
  'dark web', 'darkweb', 'darknet', 'deep web', 'onion site', 'tor browser', 'silk road',
  'cocaine', 'heroin', 'meth', 'fentanyl', 'buy drugs', 'buy weed', 'mdma', 'lsd',
  'gun', 'guns', 'firearm', 'explosive', 'bomb', 'weapon', 'weapons', 'poison',
  'hack', 'hacking', 'hacker', 'malware', 'phishing', 'crack password', 'stolen', 'counterfeit', 'fake id',
  'pirate', 'piracy', 'torrent', 'warez', 'casino', 'gambling', 'betting',
  'suicide', 'self harm', 'kill', 'murder', 'gore', 'torture', 'terrorist', 'terrorism', 'nazi',
  'fuck', 'shit', 'bitch', 'cunt', 'slut', 'whore', 'nigger', 'faggot', 'retard',
];
const PATTERNS = BLOCKED_WORDS.map((w) => new RegExp(`(^|[^a-z])${w.replace(/ /g, '[\\s-]*')}([^a-z]|$)`, 'i'));

// Domains Memo's computer may never open. The web tools are read-only and cannot reach .onion
// sites at all; this list is an extra fence around the ordinary web.
export const BLOCKED_DOMAINS = [
  'pornhub.com', 'xvideos.com', 'xnxx.com', 'xhamster.com', 'redtube.com', 'youporn.com', 'onlyfans.com',
  'chaturbate.com', 'stripchat.com', 'rule34.xxx', 'e-hentai.org', 'nhentai.net', 'spankbang.com',
  '4chan.org', '8kun.top', 'kiwifarms.net', 'thepiratebay.org', '1337x.to', 'rarbg.to',
  'bet365.com', 'stake.com', 'pokerstars.com', 'liveleak.com', 'bestgore.fun',
];

export function blockedReason(text) {
  const t = String(text || '').toLowerCase();
  const i = PATTERNS.findIndex((re) => re.test(t));
  return i >= 0 ? BLOCKED_WORDS[i] : null;
}

// Tidy up visitor text: no links, no markup, short.
export function cleanText(text, max = 200) {
  return String(text || '').replace(/https?:\/\/\S+|www\.\S+/gi, '').replace(/[<>{}\[\]`]/g, '')
    .replace(/\s+/g, ' ').trim().slice(0, max);
}
