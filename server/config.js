import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

// Load .env if present (Node 22 built-in, no dependency needed).
try { process.loadEnvFile(path.join(ROOT, '.env')); } catch { /* no .env yet */ }

const num = (v, d) => (v !== undefined && v !== '' && !Number.isNaN(Number(v)) ? Number(v) : d);
const hhmm = (v, d) => {
  const m = /^(\d{1,2}):(\d{2})$/.exec(v || '');
  return m ? Number(m[1]) * 60 + Number(m[2]) : d;
};

export const config = {
  host: process.env.HOST || '127.0.0.1',
  port: num(process.env.PORT, 4477),
  dbPath: process.env.MEMO_DB || path.join(ROOT, 'data', 'memo.db'),
  apiKeyPresent: Boolean(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN),
  demo: process.env.MEMO_DEMO === '1',
  monthlyCapUsd: num(process.env.MEMO_MONTHLY_CAP_USD, 10),
  tickMinutes: Math.max(1, num(process.env.MEMO_TICK_MINUTES, 12)),
  tickModel: process.env.MEMO_TICK_MODEL || 'claude-haiku-5-5',
  deepModel: process.env.MEMO_DEEP_MODEL || 'claude-sonnet-5-5',
  craftsPerDay: num(process.env.MEMO_CRAFTS_PER_DAY, 2),
  projectsPerDay: num(process.env.MEMO_PROJECTS_PER_DAY, 1),
  // Memo's computer (read-only web search).
  webSessionsPerDay: num(process.env.MEMO_WEB_SESSIONS_PER_DAY, 3),
  webSearchUsd: num(process.env.MEMO_WEB_SEARCH_USD, 0.01), // price of one web search
  wikiLookupsPerDay: num(process.env.MEMO_WIKI_LOOKUPS_PER_DAY, 6),
  documentsPerDay: num(process.env.MEMO_DOCUMENTS_PER_DAY, 2),
  booksDir: process.env.MEMO_BOOKS_DIR || path.join(ROOT, 'books'),
  readingsPerDay: num(process.env.MEMO_READINGS_PER_DAY, 5),
  claudeChatsPerDay: num(process.env.MEMO_CLAUDE_CHATS_PER_DAY, 2),
  programsPerDay: num(process.env.MEMO_PROGRAMS_PER_DAY, 1),
  githubToken: process.env.MEMO_GITHUB_TOKEN || '',
  githubRepo: process.env.MEMO_GITHUB_REPO || '', // for example rabbidt/memo-workshop
  // When Memo may message the Keeper.
  keeperTz: process.env.MEMO_KEEPER_TZ || 'Europe/London',
  keeperFromHour: num(process.env.MEMO_KEEPER_FROM_HOUR, 9),
  keeperToHour: num(process.env.MEMO_KEEPER_TO_HOUR, 21),
  messagesPerDay: num(process.env.MEMO_MESSAGES_PER_DAY, 3),
  notifyUrl: process.env.MEMO_NOTIFY_URL || '',
  adultXp: num(process.env.MEMO_ADULT_XP, 9000), // experience needed to be fully grown
  bedtimeMin: hhmm(process.env.MEMO_BEDTIME, 22 * 60),
  wakeMin: hhmm(process.env.MEMO_WAKETIME, 6 * 60 + 30),
};

// True when Memo should act on instinct instead of calling the API.
export const demoMode = () => config.demo || !config.apiKeyPresent;

// US dollars per million tokens: [input, output]. Checked November 2026.
// Unknown models are priced at the most expensive rate here so the cap stays safe.
export const PRICES = {
  'claude-haiku-5-5': [0.10, 0.50],
  'claude-haiku-4-5': [1, 5],
  'claude-sonnet-5-5': [2, 10],
  'claude-sonnet-5': [2, 10],
  'claude-opus-5-5': [4, 20],
  'claude-opus-5': [5, 25],
  'claude-fable-5-2': [8, 40],
};
export const FALLBACK_PRICE = [10, 50];
