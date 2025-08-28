// src/lib/api.ts
// -----------------------------------------------------------------------------
// Centraliza base de API, helpers de autenticação e o client do Setup Wizard.
// Em dev o Vite faz proxy para /api; em prod, o reverse-proxy atende /api.
// -----------------------------------------------------------------------------

export const API_BASE = "/api";

// ==== Autenticação / Perfil localStorage (compatível com seu código atual) ====
export function getToken() {
  return localStorage.getItem("auth_token");
}

export function getUser<T = any>(): T | null {
  const raw = localStorage.getItem("auth_user");
  if (!raw) return null;
  try { return JSON.parse(raw) as T; } catch { return null; }
}

export function setUser(user: any) {
  localStorage.setItem("auth_user", JSON.stringify(user || {}));
}

export function clearAuth() {
  localStorage.removeItem("auth_token");
  localStorage.removeItem("auth_user");
}

export function authHeaders() {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

// ==== HTTP helpers base ====
export async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...authHeaders(), ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`GET ${path} falhou (${res.status}): ${txt}`);
  }
  return res.json() as Promise<T>;
}

export async function sendJSON<T>(
  path: string,
  body?: any,
  method = "POST",
  extra?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(extra?.headers || {}) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    ...extra,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${method} ${path} falhou (${res.status}): ${txt}`);
  }
  // Pode retornar 204 em alguns casos
  try { return (await res.json()) as T; } catch { return {} as T; }
}

// ==== Client do Wizard de Setup (alinhado ao backend) ====
export type SetupStatus = { allowed: boolean; locked: boolean };

export type ZabbixConfig = {
  api_url: string;
  web_url: string;
  user: string;
  password: string;
};

export type MySQLConfig = {
  host: string;   // pode receber host:porta
  user: string;
  password: string;
  database: string;
};

export type SMTPConfig = {
  username: string;
  password: string;
  mail_from: string;
  server: string;
  port: number;
  starttls: boolean;
  ssl_tls: boolean;
};

export type JWTConfig = {
  secret?: string;
  alg: string;                // ex: HS256
  access_ttl_seconds: number; // 900
  refresh_ttl_seconds: number;// 1209600
  expire_hours: number;       // 8
};

export type AdminBootstrap = {
  email: string;
  username: string;
  password?: string;          // se vazio, backend gera
};

export type SetupPayload = {
  zabbix: ZabbixConfig;
  mysql_zabbix: MySQLConfig;
  mysql_glpi: MySQLConfig;
  smtp: SMTPConfig;
  jwt: JWTConfig;
  admin: AdminBootstrap;
};

export const setupApi = {
  status: () => getJSON<SetupStatus>("/setup/status"),
  testZabbix: (cfg: ZabbixConfig) => sendJSON<{ ok: true; detail: string }>("/setup/test/zabbix", cfg),
  testMySQL: (cfg: MySQLConfig) => sendJSON<{ ok: true; detail: string }>("/setup/test/mysql", cfg),
  testMySQLGlpi: (cfg: MySQLConfig) => sendJSON<{ ok: true; detail: string }>("/setup/test/mysql_glpi", cfg),
  testSMTP: (cfg: SMTPConfig) => sendJSON<{ ok: true; detail: string }>("/setup/test/smtp", cfg),
  run: (payload: SetupPayload) => sendJSON<{
    ok: boolean;
    message: string;
    admin_credentials?: {
      email: string;
      username: string;
      password_generated: boolean;
      password?: string | null;
    };
  }>("/setup/run", payload),
};
