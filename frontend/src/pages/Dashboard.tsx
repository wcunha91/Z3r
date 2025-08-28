// src/pages/Dashboard.tsx
// -----------------------------------------------------------------------------------
// Dashboard alinhado ao Z3Report
// - Layout padrão com Header fixo + Sidebar fixa em toda a aplicação
// - KPIs reais: Reports (PDFs), Agendamentos (configs com frequency)
// - Atividade recente: últimos PDFs de /reports/files
// - Ações rápidas: navegação para NewReport, ConfigsManager e ReportsManager
// - Forçar Agendamento: POST /reports/scheduled/run?force=true
// - Conta do usuário: Logout e Trocar Senha (modal)
// -----------------------------------------------------------------------------------

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

// Layout (sidebar + provedor)
import { SidebarProvider } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

// UI base
import { RuachLogo } from "@/components/ruach-logo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

// Dialog (modal) para trocar senha
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle,
} from "@/components/ui/dialog";

// Ícones
import {
  Bell, Search, User, LogOut, Settings, ChevronDown, BarChart3, FileText,
  Database, Users, Rocket, RefreshCw, Mail, Lock
} from "lucide-react";

// -----------------------------------------------------------------------------
// Helpers compactos de API – Usamos SEMPRE /api (mesma origem)
// -----------------------------------------------------------------------------
const API_BASE = "/api"; // dev: Vite proxy; prod: reverse-proxy
function authHeaders() {
  const t = localStorage.getItem("auth_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}
async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { headers: { ...authHeaders() } });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`GET ${path} falhou (${res.status}): ${txt}`);
  }
  return res.json() as Promise<T>;
}

// --- Helpers para visualizar/baixar com Authorization ------------------------
async function previewWithAuth(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { ...authHeaders() } });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Falha ao abrir (${res.status}): ${t}`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  // não revogar imediatamente para não matar a aba nova; opcional revogar depois de alguns segundos
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

async function downloadWithAuth(path: string) {
  const res = await fetch(`${API_BASE}${path}`, { headers: { ...authHeaders() } });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Falha ao baixar (${res.status}): ${t}`);
  }
  const blob = await res.blob();

  const cd = res.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)/i);
  const filename = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "arquivo.pdf";

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

// -----------------------------------------------------------------------------
// Tipagens
// -----------------------------------------------------------------------------
type ReportFile = {
  filename: string;
  size_bytes: number;
  size_human: string;
  created_at: string;   // "YYYY-MM-DD HH:mm:ss"
  modified_at: string;  // "YYYY-MM-DD HH:mm:ss"
  url_download: string; // começa com /reports/files/...
  url_preview: string;  // começa com /reports/files/...
};

type ConfigListItem = string;
type ConfigObject = {
  frequency?: "daily" | "weekly" | "monthly" | "custom" | string;
  [k: string]: any;
};

type UserOut = {
  email: string;
  username: string;
  name: string;
  role: string;
  must_change_password: boolean;
};

// -----------------------------------------------------------------------------
// Produtos do menu central (apenas navegação interna/estado visual)
// -----------------------------------------------------------------------------
const productItems = [
  { name: "Z3Report", href: "/dashboard/z3report", description: "Relatórios avançados" },
  { name: "Analytics Pro", href: "/dashboard/analytics", description: "Análise de dados" },
  { name: "Data Hub", href: "/dashboard/data", description: "Gerenciamento de dados" },
];

// -----------------------------------------------------------------------------
// Página principal
// -----------------------------------------------------------------------------
export default function Dashboard() {
  const navigate = useNavigate();
  const [activeProduct, setActiveProduct] = useState("Z3Report");

  // Estado do usuário logado (opcional, só para exibir nome/role)
  const [user, setUser] = useState<UserOut | null>(() => {
    try {
      const raw = localStorage.getItem("auth_user");
      return raw ? (JSON.parse(raw) as UserOut) : null;
    } catch {
      return null;
    }
  });

  // ---------------- KPIs / Dados ----------------
  const [loading, setLoading] = useState(false);
  const [reports, setReports] = useState<ReportFile[]>([]);
  const [configs, setConfigs] = useState<ConfigListItem[]>([]);
  const [scheduledCount, setScheduledCount] = useState<number>(0);

  // Placeholders (trocar quando houver APIs específicas)
  const [dataSourcesCount] = useState<number>(8);
  const [activeUsersCount] = useState<number>(156);

  const recentActivity = useMemo(() => reports.slice(0, 6), [reports]);
  const reportsCount = reports.length;

  // Carrega PDFs
  const loadReports = async () => {
    try {
      const data = await getJSON<ReportFile[]>("/reports/files");
      setReports(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
    }
  };

  // Carrega lista de configs e calcula quantos têm frequency definida
  const loadConfigsAndScheduled = async () => {
    try {
      const list = await getJSON<ConfigListItem[]>("/configs/");
      setConfigs(list || []);

      // Busca conteúdo de cada config para verificar frequency
      const details = await Promise.all(
        (list || []).map(async (name) => {
          try {
            const j = await getJSON<ConfigObject>(`/configs/${encodeURIComponent(name)}`);
            return j;
          } catch {
            return null;
          }
        })
      );

      const count = details.filter(
        (cfg) => cfg && typeof cfg?.frequency === "string" && cfg.frequency.length > 0
      ).length;
      setScheduledCount(count);
    } catch (err) {
      console.error(err);
    }
  };

  // Botão "Forçar Agendamento"
  const handleForceSchedule = async () => {
    if (!confirm("Deseja forçar a execução dos relatórios agendados agora?")) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/reports/scheduled/run?force=false`, {
        method: "POST",
        headers: { ...authHeaders() },
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao executar agendados (${res.status}): ${txt}`);
      }
      const data = await res.json().catch(() => ({}));
      alert(
        data?.status === "ok"
          ? "Agendados executados com sucesso! Os e-mails serão enviados em background."
          : data?.message || "Execução concluída."
      );
      // pós-execução: atualizar lista de reports para refletir novos PDFs
      await loadReports();
    } catch (err) {
      console.error(err);
      alert("Erro ao executar agendados.");
    } finally {
      setLoading(false);
    }
  };

  // Logout (padrão)
  const handleLogout = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    navigate("/", { replace: true });
  };

  // Trocar senha (modal)
  const [pwOpen, setPwOpen] = useState(false);
  const [pwCurrent, setPwCurrent] = useState("");
  const [pwNew, setPwNew] = useState("");
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState<string | null>(null);

  const submitChangePassword = async () => {
    setPwError(null);
    setPwSuccess(null);
    if (!pwCurrent || !pwNew) {
      setPwError("Preencha os dois campos.");
      return;
    }
    if (pwNew.length < 8) {
      setPwError("A nova senha deve ter pelo menos 8 caracteres.");
      return;
    }
    try {
      setPwLoading(true);
      const res = await fetch(`${API_BASE}/auth/change-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({ current_password: pwCurrent, new_password: pwNew }),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao trocar senha (${res.status}): ${txt}`);
      }
      const updatedUser = (await res.json()) as UserOut;
      localStorage.setItem("auth_user", JSON.stringify(updatedUser));
      setUser(updatedUser);
      setPwSuccess("Senha alterada com sucesso!");
      setPwCurrent("");
      setPwNew("");
      // Fecha modal depois de um pequeno feedback visual
      setTimeout(() => setPwOpen(false), 600);
    } catch (e: any) {
      setPwError(e?.message || "Erro ao trocar senha.");
    } finally {
      setPwLoading(false);
    }
  };

  // Carga inicial
  useEffect(() => {
    setLoading(true);
    Promise.all([loadReports(), loadConfigsAndScheduled()])
      .catch((e) => console.error(e))
      .finally(() => setLoading(false));
  }, []);

  return (
    <SidebarProvider>
      <div className="min-h-screen w-full bg-gradient-subtle">
        {/* Header Superior – fixo em toda a aplicação */}
        <header className="h-16 bg-background border-b border-border shadow-sm sticky top-0 z-40">
          <div className="flex items-center justify-between h-full px-4">
            {/* Branding */}
            <div className="flex items-center gap-4">
              <RuachLogo size="sm" />
            </div>

            {/* Menu de Produtos (Centro) */}
            <nav className="hidden md:flex items-center gap-1">
              {productItems.map((product) => (
                <Button
                  key={product.name}
                  variant={activeProduct === product.name ? "default" : "ghost"}
                  className={`h-9 px-4 ${
                    activeProduct === product.name
                      ? "btn-ruach-primary"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => setActiveProduct(product.name)}
                >
                  {product.name}
                </Button>
              ))}
            </nav>

            {/* Ações do Usuário (Direita) */}
            <div className="flex items-center gap-3">
              {/* Busca (placeholder) */}
              <div className="hidden lg:flex items-center relative">
                <Search className="absolute left-3 h-4 w-4 text-muted-foreground" />
                <Input placeholder="Buscar..." className="w-64 pl-10 input-ruach" />
              </div>

              {/* Notificações */}
              <Button variant="ghost" size="icon" className="relative" title="Notificações">
                <Bell className="h-5 w-5" />
                <span className="absolute -top-1 -right-1 h-3 w-3 bg-destructive rounded-full text-[10px] text-destructive-foreground flex items-center justify-center">
                  3
                </span>
              </Button>

              {/* Menu do Usuário (Perfil, Config, Trocar Senha, Sair) */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 h-9 px-3">
                    <Avatar className="h-7 w-7">
                      <AvatarImage src="/api/placeholder/32/32" alt="Usuário" />
                      <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                        {(user?.name || user?.username || "RU").slice(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="hidden md:flex flex-col items-start text-xs">
                      <span className="font-medium">{user?.name || user?.username || "Ruach User"}</span>
                      <span className="text-muted-foreground">{user?.role || "User"}</span>
                    </div>
                    <ChevronDown className="h-3 w-3 hidden md:block" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>Minha Conta</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => navigate("/dashboard")}>
                    <User className="mr-2 h-4 w-4" />
                    <span>Perfil</span>
                  </DropdownMenuItem>
                  {/* Trocar Senha */}
                  <DropdownMenuItem onClick={() => setPwOpen(true)}>
                    <Lock className="mr-2 h-4 w-4" />
                    <span>Trocar Senha</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive focus:text-destructive" onClick={handleLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Sair</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </header>

        {/* Corpo com Sidebar fixa + conteúdo rolável */}
        <div className="flex min-h-[calc(100vh-4rem)] w-full">
          {/* Sidebar fixa da aplicação */}
          <AppSidebar />

          {/* Conteúdo Principal */}
          <main className="flex-1 p-6 overflow-auto">
            <div className="max-w-7xl mx-auto space-y-6">
              {/* Welcome Section */}
              <div className="space-y-2">
                <h1 className="text-3xl font-bold text-foreground">Bem-vindo ao {activeProduct}</h1>
                <p className="text-muted-foreground text-lg">Visualize. Entenda. Decida.</p>
              </div>

              {/* Barra de ações (forçar agendamento + refresh) */}
              <div className="flex flex-wrap items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setLoading(true);
                    Promise.all([loadReports(), loadConfigsAndScheduled()])
                      .catch((e) => console.error(e))
                      .finally(() => setLoading(false));
                  }}
                  disabled={loading}
                >
                  <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                  Atualizar Dados
                </Button>

                <Button variant="secondary" onClick={handleForceSchedule} disabled={loading}>
                  <Rocket className="mr-2 h-4 w-4" />
                  Forçar Agendamento (scheduler)
                </Button>
              </div>

              {/* Quick Stats */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="card-ruach p-6">
                  <div className="flex items-center gap-3">
                    <div className="p-3 rounded-lg" style={{ background: "var(--gradient-primary)" }}>
                      <BarChart3 className="h-6 w-6 text-primary-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Relatórios Gerados</p>
                      <p className="text-2xl font-bold">{reportsCount}</p>
                    </div>
                  </div>
                </div>

                <div className="card-ruach p-6">
                  <div className="flex items-center gap-3">
                    <div className="p-3 rounded-lg" style={{ background: "var(--gradient-gold)" }}>
                      <FileText className="h-6 w-6 text-accent-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Agendamentos</p>
                      <p className="text-2xl font-bold">{scheduledCount}</p>
                    </div>
                  </div>
                </div>

                <div className="card-ruach p-6">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-primary rounded-lg">
                      <Database className="h-6 w-6 text-primary-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Fontes de Dados</p>
                      <p className="text-2xl font-bold">{dataSourcesCount}</p>
                    </div>
                  </div>
                </div>

                <div className="card-ruach p-6">
                  <div className="flex items-center gap-3">
                    <div className="p-3 bg-secondary rounded-lg">
                      <Users className="h-6 w-6 text-secondary-foreground" />
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Usuários Ativos</p>
                      <p className="text-2xl font-bold">{activeUsersCount}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Área de conteúdo */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Atividade Recente */}
                <div className="lg:col-span-2 space-y-6">
                  <div className="card-ruach p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold">Atividade Recente</h3>
                      <div className="text-xs text-muted-foreground">
                        {loading ? "Carregando..." : `${reportsCount} arquivos`}
                      </div>
                    </div>
                    <div className="space-y-3">
                      {recentActivity.length ? (
                        recentActivity.map((rf, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                          >
                            <div className="min-w-0">
                              <p className="font-medium truncate">{rf.filename}</p>
                              <p className="text-xs text-muted-foreground">
                                Modificado em {rf.modified_at} • {rf.size_human}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={async () => {
                                  try {
                                    await previewWithAuth(rf.url_preview);
                                  } catch (err) {
                                    console.error(err);
                                    alert("Erro ao abrir relatório.");
                                  }
                                }}
                                title="Visualizar"
                              >
                                <EyeIcon />
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={async () => {
                                  try {
                                    await downloadWithAuth(rf.url_download);
                                  } catch (err) {
                                    console.error(err);
                                    alert("Erro ao baixar relatório.");
                                  }
                                }}
                                title="Baixar"
                              >
                                <FileText className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={async () => {
                                  const emails = prompt("E-mails (separados por vírgula) para enviar este PDF:");
                                  if (!emails) return;
                                  try {
                                    const body = {
                                      emails: emails.split(",").map((e) => e.trim()).filter(Boolean),
                                      hostgroup_name: undefined,
                                      periodo: undefined,
                                      analyst: undefined,
                                      comments: undefined,
                                      logo_filename: undefined,
                                    };
                                    const res = await fetch(
                                      `${API_BASE}/reports/files/${encodeURIComponent(rf.filename)}/email`,
                                      {
                                        method: "POST",
                                        headers: { "Content-Type": "application/json", ...authHeaders() },
                                        body: JSON.stringify(body),
                                      }
                                    );
                                    if (!res.ok) {
                                      const t = await res.text().catch(() => "");
                                      throw new Error(`Falha ao enviar (${res.status}): ${t}`);
                                    }
                                    alert("E-mail agendado com sucesso!");
                                  } catch (err) {
                                    console.error(err);
                                    alert("Erro ao agendar envio de e-mail.");
                                  }
                                }}
                                title="Enviar por e-mail"
                              >
                                <Mail className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-muted-foreground">
                          Nenhum relatório encontrado ainda.
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Sidebar de Ações Rápidas */}
                <div className="space-y-6">
                  <div className="card-ruach p-6">
                    <h3 className="text-lg font-semibold mb-4">Ações Rápidas</h3>
                    <div className="space-y-3">
                      <Button
                        className="w-full btn-ruach-primary justify-start"
                        onClick={() => navigate("/reports/new")}
                      >
                        <FileText className="mr-2 h-4 w-4" />
                        Novo Relatório
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => navigate("/configs")}
                      >
                        <BarChart3 className="mr-2 h-4 w-4" />
                        Gerenciar Configurações
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => navigate("/reports")}
                      >
                        <Database className="mr-2 h-4 w-4" />
                        Gerenciar Relatórios
                      </Button>
                    </div>
                  </div>

                  <div className="card-ruach p-6">
                    <h3 className="text-lg font-semibold mb-4">Performance</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-sm">Relatórios Concluídos</span>
                        <span className="text-sm font-medium">
                          {reportsCount ? Math.min(99, Math.round((reportsCount / (reportsCount + 15)) * 100)) : 0}%
                        </span>
                      </div>
                      <div className="w-full bg-muted h-2 rounded-full">
                        <div
                          className="h-2 rounded-full"
                          style={{
                            width: `${reportsCount ? Math.min(99, Math.round((reportsCount / (reportsCount + 15)) * 100)) : 0}%`,
                            background: "var(--gradient-primary)",
                          }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {reportsCount} relatórios processados (últimos {reportsCount + 15})
                      </p>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </main>
        </div>
      </div>

      {/* Modal: Trocar Senha */}
      <Dialog open={pwOpen} onOpenChange={setPwOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Trocar Senha</DialogTitle>
            <DialogDescription>
              Por segurança, use ao menos 8 caracteres. Você permanecerá conectado após a troca.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-3 py-2">
            <div className="grid gap-1">
              <label className="text-sm font-medium" htmlFor="pwCurrent">Senha atual</label>
              <Input
                id="pwCurrent"
                type="password"
                value={pwCurrent}
                onChange={(e) => setPwCurrent(e.target.value)}
                placeholder="Digite sua senha atual"
              />
            </div>
            <div className="grid gap-1">
              <label className="text-sm font-medium" htmlFor="pwNew">Nova senha</label>
              <Input
                id="pwNew"
                type="password"
                value={pwNew}
                onChange={(e) => setPwNew(e.target.value)}
                placeholder="Mínimo 8 caracteres"
              />
            </div>

            {pwError && <div className="text-sm text-destructive">{pwError}</div>}
            {pwSuccess && <div className="text-sm text-green-600">{pwSuccess}</div>}
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setPwOpen(false)} disabled={pwLoading}>
              Cancelar
            </Button>
            <Button className="btn-ruach-primary" onClick={submitChangePassword} disabled={pwLoading}>
              {pwLoading ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SidebarProvider>
  );
}

// Ícone simples para "olho" (evita importar outro pacote)
function EyeIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none">
      <path
        d="M1.5 12s4-7.5 10.5-7.5S22.5 12 22.5 12 18.5 19.5 12 19.5 1.5 12 1.5 12Z"
        stroke="currentColor"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}
