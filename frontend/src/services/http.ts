// src/services/http.ts
// Wrapper simples para fetch, já apontando para /api (mesma origem).
export const API_BASE = "/api";

export async function apiGet<T = any>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} - ${txt}`);
  }
  return (await res.json()) as T;
}

export async function apiPost<T = any>(url: string, body?: any, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    credentials: "include",
    body: body != null ? JSON.stringify(body) : undefined,
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} - ${txt}`);
  }
  try {
    return (await res.json()) as T;
  } catch {
    // algumas rotas podem devolver 204/sem corpo
    return {} as T;
  }
}

export async function apiDelete<T = any>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "DELETE",
    credentials: "include",
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} - ${txt}`);
  }
  try {
    return (await res.json()) as T;
  } catch {
    return {} as T;
  }
}
