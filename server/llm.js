// Every call to Claude goes through here, so every call is checked against the spend cap first
// and recorded afterwards.
import Anthropic from '@anthropic-ai/sdk';
import { run, emit } from './db.js';
import { config } from './config.js';
import { canAfford, record } from './budget.js';

let client = null;
const anthropic = () => (client ??= new Anthropic());

export class BudgetError extends Error {}
export async function callClaude(purpose, params) {
  const chars = JSON.stringify([params.system, params.messages, params.tools]).length;
  if (!canAfford(params.model, chars, params.max_tokens)) throw new BudgetError('monthly cap reached');
  const withEffort = params.model === 'claude-haiku-4-5' ? { ...params } : { output_config: { effort: params.effort || 'low' }, ...params };
  delete withEffort.effort;
  let res;
  try { res = await anthropic().messages.create(withEffort); }
  catch (e) {
    // If this model does not take the effort setting, carry on without it rather than leave Ash stuck.
    if (e?.status !== 400 || !withEffort.output_config || !/effort|output_config/i.test(String(e?.message))) throw e;
    delete withEffort.output_config;
    res = await anthropic().messages.create(withEffort);
  }
  let cost = record(params.model, purpose, res.usage);
  const searches = res.usage?.server_tool_use?.web_search_requests || 0;
  if (searches) {
    const extra = searches * config.webSearchUsd;
    run('UPDATE spend SET cost_usd = cost_usd + ? WHERE id = (SELECT MAX(id) FROM spend)', extra);
    cost += extra;
  }
  emit('budget');
  return { res, cost };
}
export const toolUses = (res) => res.content.filter((b) => b.type === 'tool_use');
export const textOf = (res) => res.content.filter((b) => b.type === 'text').map((b) => b.text).join(' ').replace(/\s+/g, ' ').trim();
