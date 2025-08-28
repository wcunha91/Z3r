// src/lib/api.ts
// Centraliza base da API e headers (JWT + Dev Header opcional)

export const API_BASE =
  import.meta.env.VITE_API_BASE?.toString() || "/api";

/**
 * Header que simula o proxy **apenas em DEV**.
 * Em produção NÃO adicione esse header — o reverse-proxy real injetará.
 * Defina VITE_INTERNAL_PROXY_HEADER=1 no .env.development para ativar.
 */
export function devHeaders(): Record<string, string> {
  const isDev = import.meta.env.DEV;
  const marker = import.meta.env.VITE_INTERNAL_PROXY_HEADER;
  if (isDev && marker) {
    return { "X-Internal-Proxy": String(marker) };
  }
  return {};
}

export function getToken() {
  return localStorage.getItem("auth_token");
}
export function setToken(t: string) {
  localStorage.setItem("auth_token", t);
}
export function setUser(u: any) {
  localStorage.setItem("auth_user", JSON.stringify(u || {}));
}
export function clearAuth() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}

export function authHeaders(): Record<string, string> {
  const t = getToken();
  const h: Record<string, string> = { ...devHeaders() };
  if (t) h.Authorization = `Bearer ${t}`;
  return h;
}

export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} -> ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function postJSON<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
    body: JSON.stringify(body ?? {}),
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} -> ${res.status} ${text}`);
  }
  return res.json() as Promise<T>;
}
