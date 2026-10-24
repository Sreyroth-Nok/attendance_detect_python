/**
 * Thin fetch wrapper: JSON in/out, admin API key header, and normalized errors.
 * Every failed request throws an ApiError carrying the backend's error envelope.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
const KEY_STORAGE = 'sms.adminApiKey';

export class ApiError extends Error {
  constructor(status, code, message, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** Field errors as { field: message } for forms. */
  get fieldErrors() {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      this.details.filter((d) => d.field).map((d) => [d.field, d.message]),
    );
  }
}

// --- admin API key (kept in sessionStorage unless the user chooses to remember it) ---

function storage(kind) {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
}

export function getApiKey() {
  return storage('session')?.getItem(KEY_STORAGE) || storage('local')?.getItem(KEY_STORAGE) || '';
}

export function isApiKeyRemembered() {
  return Boolean(storage('local')?.getItem(KEY_STORAGE));
}

export function setApiKey(key, { remember = false } = {}) {
  try {
    storage('session')?.removeItem(KEY_STORAGE);
    storage('local')?.removeItem(KEY_STORAGE);
    if (key) storage(remember ? 'local' : 'session')?.setItem(KEY_STORAGE, key);
  } catch {
    // Storage can be unavailable (private mode); the key then lasts only for this page.
  }
}

// --- requests ---

function buildUrl(path, params) {
  const url = new URL(BASE_URL + path, window.location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') url.searchParams.set(key, value);
  });
  return BASE_URL ? url.toString() : url.pathname + url.search;
}

async function parseError(response) {
  let body = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error (proxy or server crash).
  }
  const err = body?.error;
  if (err) return new ApiError(response.status, err.code, err.message, err.details);
  const fallback =
    response.status === 502 || response.status === 504
      ? 'The API server is not reachable. Make sure the backend is running.'
      : `Request failed (${response.status}).`;
  return new ApiError(response.status, 'http_error', fallback);
}

export async function request(path, { method = 'GET', params, json, formData, raw = false } = {}) {
  const headers = { Accept: raw ? '*/*' : 'application/json' };
  const key = getApiKey();
  if (key) headers['X-API-Key'] = key;

  let body;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (formData) {
    body = formData;
  }

  let response;
  try {
    response = await fetch(buildUrl(path, params), { method, headers, body });
  } catch {
    throw new ApiError(
      0,
      'network_error',
      'Cannot reach the server. Check your connection and that the backend is running.',
    );
  }

  if (!response.ok) throw await parseError(response);
  if (raw) return response;
  if (response.status === 204) return null;
  return response.json();
}

/** Download a file response (e.g. CSV export) using the server-provided filename. */
export async function downloadFile(path, params, fallbackName) {
  const response = await request(path, { params, raw: true });
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || fallbackName;

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return filename;
}
