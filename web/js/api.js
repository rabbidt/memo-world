// Talks to the island server. The key from your link is kept in this browser and sent with each request.
const url = new URL(location.href);
const fromLink = url.searchParams.get('k');
if (fromLink) {
  try { localStorage.setItem('memo_key', fromLink); } catch { /* private window */ }
  url.searchParams.delete('k');
  history.replaceState(null, '', url);
}
let stored = null;
try { stored = localStorage.getItem('memo_key'); } catch { /* private window */ }
export const key = fromLink || stored || '';
export const params = url.searchParams;

export async function api(path, body) {
  const res = await fetch(`/api/${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'x-memo-key': key, ...(body ? { 'Content-Type': 'application/json' } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || `Request failed (${res.status})`), { status: res.status });
  return data;
}

export function stream(onMessage) {
  const es = new EventSource(`/api/stream?k=${encodeURIComponent(key)}`);
  es.onmessage = (e) => { try { onMessage(JSON.parse(e.data)); } catch (err) { console.error(err); } };
  return es;
}
