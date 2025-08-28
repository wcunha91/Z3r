// src/lib/fetch-patch.ts
// Patch global do fetch para:
// 1) Detectar chamadas ao backend (relativas ou absolutas) e prefixar /api quando fizer sentido
// 2) Anexar Authorization: Bearer <token> SEMPRE que for chamada ao backend (exceto /auth/login)
// 3) Anexar X-Internal-Proxy em DEV (se configurado)

const originalFetch = window.fetch;

// Rotas conhecidas do backend (ajuste se tiver mais)
const BACKEND_PREFIXES = ["/auth", "/reports", "/configs", "/zabbix", "/glpi"];

// Hosts do backend em DEV que podem aparecer como URL absoluta:
const BACKEND_HOSTS = new Set<string>([
  "localhost:8000",
  "127.0.0.1:8000",
]);

function parseUrl(input: RequestInfo | URL): URL {
  if (typeof input === "string") {
    try {
      // absoluta
      return new URL(input);
    } catch {
      // relativa -> resolver contra a origem atual
      return new URL(input, window.location.origin);
    }
  } else if (input instanceof URL) {
    return input;
  } else {
    const req = input as Request;
    try {
      return new URL(req.url);
    } catch {
      return new URL(req.url, window.location.origin);
    }
  }
}

function isBackendPath(pathname: string): boolean {
  return BACKEND_PREFIXES.some((p) => pathname === p || pathname.startsWith(p + "/"));
}

function isDevBackendHost(url: URL): boolean {
  return BACKEND_HOSTS.has(url.host);
}

function devProxyHeader(): Record<string, string> {
  if (import.meta.env.DEV && import.meta.env.VITE_INTERNAL_PROXY_HEADER) {
    return { "X-Internal-Proxy": String(import.meta.env.VITE_INTERNAL_PROXY_HEADER) };
  }
  return {};
}

function isAuthLoginPath(pathname: string): boolean {
  return pathname === "/auth/login" || pathname === "/api/auth/login";
}

window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  // 1) Normaliza URL
  const urlObj = parseUrl(input);
  let pathname = urlObj.pathname;

  // 2) Detecta se é chamada ao backend:
  //    - URL absoluta para localhost:8000/127.0.0.1:8000
  //    - OU URL relativa cujo pathname bate nos prefixos do backend
  const absoluteToDevBackend = isDevBackendHost(urlObj);
  const relativeToBackend = urlObj.origin === window.location.origin && isBackendPath(pathname);
  const isBackendCall = absoluteToDevBackend || relativeToBackend || pathname.startsWith("/api/");

  // 3) Se for chamada relativa a backend e NÃO tem /api no começo, prefixa /api
  //    (isso faz a requisição passar pelo proxy do Vite)
  let finalUrl = urlObj.href;
  if (relativeToBackend && !pathname.startsWith("/api/")) {
    pathname = `/api${pathname}`;
    finalUrl = `${window.location.origin}${pathname}${urlObj.search}${urlObj.hash}`;
  }

  // 4) Monta headers preservando existentes
  const headers = new Headers(
    (init && init.headers) ||
      (typeof input !== "string" && !(input instanceof URL) ? (input as Request).headers : undefined)
  );

  // 5) Header de DEV
  const devHdr = devProxyHeader();
  Object.entries(devHdr).forEach(([k, v]) => headers.set(k, v));

  // 6) Authorization: Bearer (para qualquer chamada ao backend, exceto /auth/login)
  const token = localStorage.getItem("auth_token");
  const loginPath =
    isAuthLoginPath(urlObj.pathname) || isAuthLoginPath(pathname);

  if (isBackendCall && !loginPath && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // 7) Envia
  const finalInit: RequestInit = { ...init, headers };
  return originalFetch(finalUrl, finalInit);
};
