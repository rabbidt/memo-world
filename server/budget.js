// Hard monthly spend cap. Every API call is checked against it first and recorded after.
import { all, get, run, nowIso } from './db.js';
import { config, PRICES, FALLBACK_PRICE } from './config.js';

export const monthKey = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
const price = (model) => PRICES[model] || FALLBACK_PRICE;

export function spentThisMonth() {
  return get('SELECT COALESCE(SUM(cost_usd), 0) AS s FROM spend WHERE month = ?', monthKey()).s;
}

export function costOf(model, usage) {
  const [pin, pout] = price(model);
  const input = usage.input_tokens || 0, output = usage.output_tokens || 0;
  const cr = usage.cache_read_input_tokens || 0, cw = usage.cache_creation_input_tokens || 0;
  return (input * pin + cr * pin * 0.1 + cw * pin * 1.25 + output * pout) / 1e6;
}

// Worst case for a call we are about to make: all of the prompt plus every allowed output token.
export function worstCase(model, promptChars, maxTokens) {
  const [pin, pout] = price(model);
  return ((promptChars / 2.5) * pin + maxTokens * pout) / 1e6;
}

export function canAfford(model, promptChars, maxTokens) {
  return spentThisMonth() + worstCase(model, promptChars, maxTokens) <= config.monthlyCapUsd;
}

export function record(model, purpose, usage) {
  const cost = costOf(model, usage);
  run(`INSERT INTO spend(ts, month, model, purpose, input_tokens, output_tokens, cache_read, cache_write, cost_usd)
    VALUES(?,?,?,?,?,?,?,?,?)`, nowIso(), monthKey(), model, purpose, usage.input_tokens || 0,
    usage.output_tokens || 0, usage.cache_read_input_tokens || 0, usage.cache_creation_input_tokens || 0, cost);
  return cost;
}

export function budgetSummary() {
  const spent = spentThisMonth();
  const byPurpose = all('SELECT purpose, COUNT(*) AS calls, SUM(cost_usd) AS cost FROM spend WHERE month = ? GROUP BY purpose', monthKey());
  return { month: monthKey(), spent, cap: config.monthlyCapUsd, exhausted: spent >= config.monthlyCapUsd * 0.995, byPurpose };
}
