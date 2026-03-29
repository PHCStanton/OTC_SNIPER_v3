/**
 * Shared JSON HTTP request helper for the frontend API clients.
 */
export async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(`/api${path}`, opts);
  const data = await res.json().catch(() => ({}));

  if (!res.ok) {
    const msg = data.detail || data.message || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}