// src/services/auth.ts
import { API_BASE, setToken, setUser, devHeaders } from "@/lib/api";

type UserOut = {
  id: string;
  username: string;
  name: string;
  role: string;
  must_change_password: boolean;
};

type LoginOut = {
  access_token: string;
  token_type: string;
  user: UserOut;
};

export async function login(identifier: string, password: string): Promise<LoginOut> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...devHeaders() },
    body: JSON.stringify({ identifier, password }),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Login falhou (${res.status}): ${txt}`);
  }
  const data = (await res.json()) as LoginOut;
  setToken(data.access_token);
  setUser(data.user);
  return data;
}

export async function me(): Promise<UserOut> {
  const token = localStorage.getItem("auth_token");
  if (!token) throw new Error("Sem token");

  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: { Authorization: `Bearer ${token}`, ...devHeaders() },
  });
  if (!res.ok) throw new Error("Não autenticado");
  return (await res.json()) as UserOut;
}
