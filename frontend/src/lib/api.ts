// Thin fetch wrapper: injects the JWT, normalizes errors, handles 401.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";
const TOKEN_KEY = "priya_token";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

// Notify the app (AuthContext) when a request is rejected as unauthorized.
type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;
export function setUnauthorizedHandler(fn: UnauthorizedHandler | null): void {
  onUnauthorized = fn;
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
      return data.detail
        .map((d: { loc?: string[]; msg?: string }) =>
          `${(d.loc || []).slice(1).join(".")}: ${d.msg}`
        )
        .join("; ");
    }
    return JSON.stringify(data);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 401) {
    setToken(null);
    onUnauthorized?.();
    throw new ApiError(401, "Session expired. Please sign in again.");
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export interface RequestOptions {
  query?: Record<string, string | number | boolean | undefined | null>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${BASE_URL}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== "") params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

export const api = {
  get<T>(path: string, opts?: RequestOptions): Promise<T> {
    return fetch(buildUrl(path, opts?.query), { headers: authHeaders() }).then(
      handle<T>
    );
  },
  post<T>(path: string, body?: unknown, opts?: RequestOptions): Promise<T> {
    return fetch(buildUrl(path, opts?.query), {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).then(handle<T>);
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return fetch(buildUrl(path), {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).then(handle<T>);
  },
  del<T>(path: string): Promise<T> {
    return fetch(buildUrl(path), {
      method: "DELETE",
      headers: authHeaders(),
    }).then(handle<T>);
  },
  // Multipart upload (CSV import).
  upload<T>(path: string, form: FormData): Promise<T> {
    return fetch(buildUrl(path), {
      method: "POST",
      headers: authHeaders(), // do NOT set Content-Type; browser sets boundary
      body: form,
    }).then(handle<T>);
  },
  // Authenticated file download (CSV export) → triggers a browser download.
  async download(path: string, filename: string, opts?: RequestOptions): Promise<void> {
    const res = await fetch(buildUrl(path, opts?.query), { headers: authHeaders() });
    if (!res.ok) throw new ApiError(res.status, await parseError(res));
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
