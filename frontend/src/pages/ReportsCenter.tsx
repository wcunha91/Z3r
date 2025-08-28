// src/pages/ReportsCenter.tsx
// ----------------------------------------------------------------------------------
// Centro de Relatórios (UNIFICADO)
// - Aba "Gerados": lista PDFs, busca por nome, filtro de datas, download, enviar e-mail, excluir
// - Aba "Agendados": lista configs, frequência, período-alvo, último envio, executar (normal/force)
// - Sem preview inline (conforme pedido)
// - Integração com /api centralizado (src/lib/api.ts):
//   * API_BASE = "/api" (Vite proxy em dev, reverse-proxy em prod)
//   * authHeaders() injeta o Authorization: Bearer <token> se houver
//   * getJSON() para GETs autenticados com tratamento de erro
// - Tratativa de 401: limpa sessão e redireciona para /login
// - Download: via fetch + Blob (com Authorization), garantindo acesso autenticado
// ----------------------------------------------------------------------------------

import { useEffect, useMemo, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";

import {
  Loader2, Download, Trash2, RefreshCw, Calendar, FileText, Send,
  CalendarRange, PlayCircle, Play, Clock, CheckCircle2, AlertTriangle
} from "lucide-react";

import { API_BASE, authHeaders, getJSON, clearAuth } from "@/lib/api";

// -----------------------------------------
// Tipos (Gerados)
// -----------------------------------------
type ReportFile = {
  filename: string;
  size_bytes: number;
  size_human: string;
  created_at: string;
  modified_at: string;
  url_download: string; // ex.: /reports/files/<file>
  url_preview: string;  // não usado (preview removido)
};

// -----------------------------------------
// Tipos (Agendados)
// -----------------------------------------
type ConfigFilename = string;

type ConfigObject = {
  hostgroup?: { id?: string; name?: string };
  frequency?: "weekly" | "monthly" | string;
  last_sent_period?: string | null;
  last_sent?: string | null;
  emails?: string[];
  // demais campos serão ignorados aqui
};

type RowItem = {
  filename: string;
  cfg: ConfigObject;
  targetPeriod: string | null; // período-alvo calculado (YYYY-MM ou YYYY-WW)
  status: "pending" | "sent" | "unknown";
};

type RunResponse = {
  status: "ok" | "no_reports";
  processed?: Array<{
    filename: string;
    report_file: string;
    emails_sent: string[];
    last_generated: string;
    force: boolean;
  }>;
  message?: string;
};

// -----------------------------------------
// Helpers (Agendados)
// -----------------------------------------
function pad2(n: number) {
  return n < 10 ? `0${n}` : `${n}`;
}

/**
 * Emula o %W do Python (semana do ano começando na segunda; semana 00 até a primeira segunda).
 * Retorna o número da semana com 2 dígitos (00..53).
 */
function weekNumber_PythonPercentW(d: Date): number {
  const date = new Date(d.getTime());
  date.setHours(0, 0, 0, 0);

  const jan1 = new Date(date.getFullYear(), 0, 1);
  const jan1Day = jan1.getDay(); // 0=Dom,1=Seg,...6=Sab
  const firstMondayOffset = (8 - jan1Day) % 7;
  const firstMonday = new Date(jan1.getFullYear(), 0, 1 + firstMondayOffset);
  firstMonday.setHours(0, 0, 0, 0);

  if (date < firstMonday) {
    return 0;
  }

  const diffMs = +date - +firstMonday;
  const diffDays = Math.floor(diffMs / 86400000);
  const week = Math.floor(diffDays / 7) + 1;
  return week;
}

/** Retorna o período-alvo atual para weekly: "YYYY-WW" da semana ANTERIOR (segunda a domingo). */
function getCurrentTargetPeriodWeekly(): string {
  const now = new Date();
  const day = now.getDay(); // 0=Dom,1=Seg...
  const diffToMon = (day + 6) % 7;
  const startThisWeek = new Date(now);
  startThisWeek.setDate(now.getDate() - diffToMon);
  startThisWeek.setHours(0, 0, 0, 0);

  const startPrevWeek = new Date(startThisWeek);
  startPrevWeek.setDate(startThisWeek.getDate() - 7);

  const y = startPrevWeek.getFullYear();
  const W = weekNumber_PythonPercentW(startPrevWeek);
  return `${y}-${pad2(W)}`;
}

/** Retorna o período-alvo atual para monthly: "YYYY-MM" do mês ANTERIOR. */
function getCurrentTargetPeriodMonthly(): string {
  const now = new Date();
  const firstOfThis = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastOfPrev = new Date(firstOfThis.getTime() - 86400000);
  const y = lastOfPrev.getFullYear();
  const m = lastOfPrev.getMonth() + 1; // 1..12
  return `${y}-${pad2(m)}`;
}

// -----------------------------------------
// Helper central para requisições que NÃO são GET JSON:
// - injeta Authorization
// - trata 401 limpando sessão e redirecionando
// -----------------------------------------
async function authFetch(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  // Define Content-Type apenas quando enviando body
  if (init.method && init.method !== "GET" && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  // Injeta Authorization quando existir
  const mergedInit: RequestInit = {
    ...init,
    headers: { ...authHeaders(), ...Object.fromEntries(headers.entries()) },
  };

  const res = await fetch(`${API_BASE}${path}`, mergedInit);
  if (res.status === 401) {
    // sessão expirada: limpa auth e redireciona
    clearAuth();
    window.location.href = "/login";
    return res;
  }
  return res;
}

// -----------------------------------------
// Helper: download autenticado (fetch + Blob)
// -----------------------------------------
async function downloadWithAuth(path: string) {
  // path esperado: ex. "/reports/files/<arquivo.pdf>"
  const res = await fetch(`${API_BASE}${path}`, {
    method: "GET",
    headers: {
      ...authHeaders(), // Authorization: Bearer <token>
      // NÃO defina Content-Type aqui
    },
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`Falha ao baixar (${res.status}): ${txt}`);
  }

  const blob = await res.blob();

  // tenta extrair nome do arquivo do Content-Disposition
  const cd = res.headers.get("Content-Disposition") || "";
  const match = cd.match(/filename\*?=(?:UTF-8'')?"?([^";\n]+)/i);
  const filename = match ? decodeURIComponent(match[1].replace(/"/g, "")) : "arquivo.pdf";

  const url = URL.createObjectURL(blob);

  // Download direto:
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);

  // Se quiser abrir em nova aba (preview), troque o bloco acima por:
  // window.open(url, "_blank");
}

// ================================================================================
// Componente principal
// ================================================================================
export default function ReportsCenter() {
  // -----------------------------
  // Estados (Aba: Gerados)
  // -----------------------------
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [files, setFiles] = useState<ReportFile[]>([]);
  const [query, setQuery] = useState("");
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [refreshKeyFiles, setRefreshKeyFiles] = useState(0);

  // -----------------------------
  // Modal de e-mail (Gerados)
  // -----------------------------
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [emailTargetFilename, setEmailTargetFilename] = useState<string | null>(null);

  const [emailsField, setEmailsField] = useState("");
  const [hostgroupField, setHostgroupField] = useState("");
  const [periodoField, setPeriodoField] = useState("");
  const [analystField, setAnalystField] = useState("");
  const [commentsField, setCommentsField] = useState("");
  const [logoFilenameField, setLogoFilenameField] = useState("");

  // -----------------------------
  // Estados (Aba: Agendados)
  // -----------------------------
  const [loadingSched, setLoadingSched] = useState(false);
  const [filenames, setFilenames] = useState<ConfigFilename[]>([]);
  const [rows, setRows] = useState<RowItem[]>([]);
  const [filterSched, setFilterSched] = useState("");
  const [runOpen, setRunOpen] = useState(false);
  const [runData, setRunData] = useState<RunResponse | null>(null);

  // ======================================================================
  // Funções: Gerados
  // ======================================================================
  const fetchFiles = async () => {
    try {
      setLoadingFiles(true);
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      if (startDate) params.set("start_date", startDate.toISOString().slice(0, 10));
      if (endDate) params.set("end_date", endDate.toISOString().slice(0, 10));

      // GET JSON via helper central (trata 4xx/5xx com mensagem)
      const data = await getJSON<ReportFile[]>(`/reports/files?${params.toString()}`);
      setFiles(data);
    } catch (err) {
      console.error(err);
      alert("Erro ao listar relatórios.");
    } finally {
      setLoadingFiles(false);
    }
  };

  useEffect(() => {
    fetchFiles();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKeyFiles]);

  // >>> ALTERADO: download autenticado (sem window.open direto)
  const handleDownload = async (file: ReportFile) => {
    try {
      await downloadWithAuth(file.url_download);  // ex.: /reports/files/<file>
    } catch (err) {
      console.error(err);
      alert("Erro ao baixar relatório.");
    }
  };

  const handleDelete = async (file: ReportFile) => {
    if (!confirm(`Excluir o relatório "${file.filename}"?`)) return;
    try {
      setLoadingFiles(true);
      const res = await authFetch(`/reports/files/${encodeURIComponent(file.filename)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao excluir (${res.status}): ${txt}`);
      }
      setRefreshKeyFiles((k) => k + 1);
    } catch (err) {
      console.error(err);
      alert("Erro ao excluir relatório.");
    } finally {
      setLoadingFiles(false);
    }
  };

  const handleOpenEmailModal = (filename: string) => {
    setEmailTargetFilename(filename);
    // campos em branco por padrão (o período é textual)
    setPeriodoField("");
    setEmailsField("");
    setHostgroupField("");
    setAnalystField("");
    setCommentsField("");
    setLogoFilenameField("");
    setEmailOpen(true);
  };

  const handleSendEmail = async () => {
    if (!emailTargetFilename) return;
    const emails = emailsField
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean);

    if (emails.length === 0) {
      alert("Informe ao menos um e-mail.");
      return;
    }

    const payload = {
      emails,
      hostgroup_name: hostgroupField || undefined,
      periodo: periodoField || undefined,
      analyst: analystField || undefined,
      comments: commentsField || undefined,
      logo_filename: logoFilenameField || undefined
    };

    try {
      setEmailSending(true);
      const res = await authFetch(
        `/reports/files/${encodeURIComponent(emailTargetFilename)}/email`,
        { method: "POST", body: JSON.stringify(payload) }
      );
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao enviar e-mail (${res.status}): ${txt}`);
      }
      setEmailOpen(false);
      alert("E-mail agendado com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao agendar envio de e-mail.");
    } finally {
      setEmailSending(false);
    }
  };

  const clearFilters = () => {
    setQuery("");
    setStartDate(null);
    setEndDate(null);
    setRefreshKeyFiles((k) => k + 1);
  };

  const totalSizeHuman = useMemo(() => {
    if (!files.length) return "0 B";
    const total = files.reduce((acc, f) => acc + f.size_bytes, 0);
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = total;
    let i = 0;
    while (size >= 1024 && i < units.length - 1) {
      size /= 1024;
      i++;
    }
    return `${size.toFixed(2)} ${units[i]}`;
  }, [files]);

  // ======================================================================
  // Funções: Agendados
  // ======================================================================
  async function loadScheduledList() {
    try {
      setLoadingSched(true);
      // Lista de arquivos de config
      const list = await getJSON<ConfigFilename[]>(`/configs/`);
      setFilenames(list);

      // Carrega conteúdo de cada config em paralelo
      const loaded: RowItem[] = await Promise.all(
        list.map(async (name) => {
          try {
            const cfg = await getJSON<ConfigObject>(`/configs/${encodeURIComponent(name)}`);

            let targetPeriod: string | null = null;
            if (cfg.frequency === "weekly") {
              targetPeriod = getCurrentTargetPeriodWeekly();
            } else if (cfg.frequency === "monthly") {
              targetPeriod = getCurrentTargetPeriodMonthly();
            } else {
              targetPeriod = null; // daily/other: desconhecido para o scheduler atual
            }

            let status: RowItem["status"] = "unknown";
            if (targetPeriod && typeof cfg.last_sent_period === "string") {
              status = cfg.last_sent_period === targetPeriod ? "sent" : "pending";
            } else if (targetPeriod) {
              status = "pending";
            }

            return {
              filename: name,
              cfg,
              targetPeriod,
              status,
            } as RowItem;
          } catch {
            return {
              filename: name,
              cfg: {},
              targetPeriod: null,
              status: "unknown",
            } as RowItem;
          }
        })
      );
      setRows(loaded);
    } catch (err) {
      console.error(err);
      alert("Erro ao carregar a lista de configurações.");
    } finally {
      setLoadingSched(false);
    }
  }

  useEffect(() => {
    loadScheduledList();
  }, []);

  const filteredRows = useMemo(() => {
    const q = filterSched.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) =>
      r.filename.toLowerCase().includes(q) ||
      (r.cfg.hostgroup?.name || "").toLowerCase().includes(q)
    );
  }, [rows, filterSched]);

  async function runScheduled(force: boolean) {
    try {
      setLoadingSched(true);
      const url = `/reports/scheduled/run${force ? "?force=true" : ""}`;
      const res = await authFetch(url, { method: "POST" });
      const data: RunResponse = await res.json().catch(() => ({ status: "no_reports" } as RunResponse));
      setRunData(data);
      setRunOpen(true);
      // Recarrega lista para refletir last_sent/period atualizados
      await loadScheduledList();
    } catch (err) {
      console.error(err);
      alert("Erro ao acionar o agendamento.");
    } finally {
      setLoadingSched(false);
    }
  }

  // ======================================================================
  // Render (Tabs)
  // ======================================================================
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileText className="h-6 w-6" />
          Centro de Relatórios
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setRefreshKeyFiles((k) => k + 1)} disabled={loadingFiles}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loadingFiles ? "animate-spin" : ""}`} />
            Atualizar Arquivos
          </Button>
          <Button variant="outline" onClick={() => loadScheduledList()} disabled={loadingSched}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loadingSched ? "animate-spin" : ""}`} />
            Recarregar Agendados
          </Button>
        </div>
      </div>

      <Tabs defaultValue="gerados" className="w-full">
        <TabsList>
          <TabsTrigger value="gerados">Relatórios Gerados</TabsTrigger>
          <TabsTrigger value="agendados">Status Agendados</TabsTrigger>
        </TabsList>

        {/* ---------------------------------------------------------------- */}
        {/* ABA: Gerados                                                     */}
        {/* ---------------------------------------------------------------- */}
        <TabsContent value="gerados" className="space-y-6">
          {/* Filtros */}
          <Card>
            <CardHeader>
              <CardTitle>Filtros</CardTitle>
            </CardHeader>
            <CardContent className="grid md:grid-cols-4 gap-4">
              <div className="col-span-1">
                <Label className="text-sm mb-1">Pesquisar por nome</Label>
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ex.: cecal, hemocentro, cpu..."
                  disabled={loadingFiles}
                />
              </div>

              <div className="col-span-1">
                <Label className="text-sm mb-1">Data Inicial</Label>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <DatePicker
                    selected={startDate}
                    onChange={(d: Date | null) => setStartDate(d)}
                    dateFormat="yyyy-MM-dd"
                    className="input-ruach text-sm"
                    placeholderText="YYYY-MM-DD"
                    disabled={loadingFiles}
                  />
                </div>
              </div>

              <div className="col-span-1">
                <Label className="text-sm mb-1">Data Final</Label>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <DatePicker
                    selected={endDate}
                    onChange={(d: Date | null) => setEndDate(d)}
                    dateFormat="yyyy-MM-dd"
                    className="input-ruach text-sm"
                    placeholderText="YYYY-MM-DD"
                    disabled={loadingFiles}
                  />
                </div>
              </div>

              <div className="col-span-1 flex items-end gap-2">
                <Button onClick={fetchFiles} disabled={loadingFiles}>
                  {loadingFiles ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  Aplicar
                </Button>
                <Button variant="outline" onClick={clearFilters} disabled={loadingFiles}>
                  Limpar
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Resumo */}
          <div className="text-sm text-muted-foreground">
            {files.length} arquivo(s) • Total {totalSizeHuman}
          </div>

          {/* Tabela */}
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>Arquivos</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nome</TableHead>
                      <TableHead className="w-28">Tamanho</TableHead>
                      <TableHead className="w-44">Modificado</TableHead>
                      <TableHead className="w-[380px]">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {files.map((f) => (
                      <TableRow key={f.filename}>
                        <TableCell className="font-medium">{f.filename}</TableCell>
                        <TableCell>{f.size_human}</TableCell>
                        <TableCell>{f.modified_at}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-2">
                            <Button variant="outline" onClick={() => handleDownload(f)}>
                              <Download className="mr-2 h-4 w-4" />
                              Baixar
                            </Button>
                            <Button onClick={() => handleOpenEmailModal(f.filename)}>
                              <Send className="mr-2 h-4 w-4" />
                              Enviar por e-mail
                            </Button>
                            <Button variant="destructive" onClick={() => handleDelete(f)}>
                              <Trash2 className="mr-2 h-4 w-4" />
                              Excluir
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                    {!files.length && (
                      <TableRow>
                        <TableCell colSpan={4} className="text-center text-sm text-muted-foreground py-6">
                          Nenhum relatório encontrado para os filtros aplicados.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ---------------------------------------------------------------- */}
        {/* ABA: Agendados                                                   */}
        {/* ---------------------------------------------------------------- */}
        <TabsContent value="agendados" className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CalendarRange className="h-5 w-5" />
              <h2 className="text-xl font-semibold">Status dos Relatórios Agendados</h2>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={() => runScheduled(false)} disabled={loadingSched}>
                <Play className="mr-2 h-4 w-4" />
                Executar agendados
              </Button>
              <Button variant="secondary" onClick={() => runScheduled(true)} disabled={loadingSched}>
                <PlayCircle className="mr-2 h-4 w-4" />
                Executar agendados (force)
              </Button>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Filtros</CardTitle>
            </CardHeader>
            <CardContent className="grid md:grid-cols-3 gap-4">
              <div>
                <Label>Pesquisar por nome do arquivo ou hostgroup</Label>
                <Input
                  value={filterSched}
                  onChange={(e) => setFilterSched(e.target.value)}
                  placeholder="ex.: _config_2025-08, ou nome do hostgroup"
                  disabled={loadingSched}
                />
              </div>
            </CardContent>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>Configs agendadas</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Arquivo</TableHead>
                      <TableHead>Hostgroup</TableHead>
                      <TableHead>Frequência</TableHead>
                      <TableHead>Período-alvo</TableHead>
                      <TableHead>Último período enviado</TableHead>
                      <TableHead>Último envio</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredRows.map((r) => {
                      const freq = r.cfg.frequency || "-";
                      const hg = r.cfg.hostgroup?.name || "-";
                      const lastPeriod = r.cfg.last_sent_period || "-";
                      const lastSent = r.cfg.last_sent
                        ? new Date(r.cfg.last_sent).toLocaleString("pt-BR")
                        : "-";

                      const badge =
                        r.status === "sent" ? (
                          <Badge className="bg-emerald-600 hover:bg-emerald-600/90">
                            <CheckCircle2 className="mr-1 h-4 w-4" />
                            Enviado
                          </Badge>
                        ) : r.status === "pending" ? (
                          <Badge className="bg-amber-600 hover:bg-amber-600/90">
                            <AlertTriangle className="mr-1 h-4 w-4" />
                            Pendente
                          </Badge>
                        ) : (
                          <Badge variant="secondary">
                            <Clock className="mr-1 h-4 w-4" />
                            Desconhecido
                          </Badge>
                        );

                      return (
                        <TableRow key={r.filename}>
                          <TableCell className="font-medium">{r.filename}</TableCell>
                          <TableCell>{hg}</TableCell>
                          <TableCell className="uppercase">{freq}</TableCell>
                          <TableCell>{r.targetPeriod || "-"}</TableCell>
                          <TableCell>{lastPeriod}</TableCell>
                          <TableCell>{lastSent}</TableCell>
                          <TableCell>{badge}</TableCell>
                        </TableRow>
                      );
                    })}
                    {!filteredRows.length && (
                      <TableRow>
                        <TableCell colSpan={7} className="text-center text-sm text-muted-foreground py-6">
                          Nenhuma configuração encontrada.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* MODAL DE E-MAIL (Arquivos Gerados) */}
      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>Enviar por e-mail</DialogTitle>
            <DialogDescription>
              {emailTargetFilename ? `Arquivo: ${emailTargetFilename}` : ""}
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label>E-mails (separados por vírgula) *</Label>
              <Input
                placeholder="ex.: pessoa@dominio.com, outro@dominio.com"
                value={emailsField}
                onChange={(e) => setEmailsField(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>Hostgroup (opcional)</Label>
              <Input
                placeholder="Nome do grupo/cliente"
                value={hostgroupField}
                onChange={(e) => setHostgroupField(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>Período (opcional)</Label>
              <Input
                placeholder="YYYY-MM-DD a YYYY-MM-DD"
                value={periodoField}
                onChange={(e) => setPeriodoField(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>Analista (opcional)</Label>
              <Input
                placeholder="Nome do analista"
                value={analystField}
                onChange={(e) => setAnalystField(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>Comentários (opcional)</Label>
              <Textarea
                placeholder="Mensagem adicional que aparecerá no e-mail"
                value={commentsField}
                onChange={(e) => setCommentsField(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>Logo (opcional) — arquivo em configs/logos/</Label>
              <Input
                placeholder="ex.: logo_cliente.png"
                value={logoFilenameField}
                onChange={(e) => setLogoFilenameField(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailOpen(false)} disabled={emailSending}>
              Cancelar
            </Button>
            <Button onClick={handleSendEmail} disabled={emailSending}>
              {emailSending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              Enviar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* MODAL: resultado da execução (Agendados) */}
      <Dialog open={runOpen} onOpenChange={setRunOpen}>
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>Resultado da execução agendada</DialogTitle>
          </DialogHeader>
          {!runData ? (
            <div className="text-sm text-muted-foreground">Sem dados.</div>
          ) : runData.status === "no_reports" ? (
            <div className="text-sm">
              Nenhum relatório foi executado neste ciclo.
              {runData.message ? <div className="text-muted-foreground mt-1">{runData.message}</div> : null}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="text-sm">
                Total processado: <b>{runData.processed?.length ?? 0}</b>
              </div>
              <div className="border rounded-md overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Config</TableHead>
                      <TableHead>Arquivo gerado</TableHead>
                      <TableHead>Destinatários</TableHead>
                      <TableHead>Gerado em</TableHead>
                      <TableHead>Force</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(runData.processed || []).map((p, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-medium">{p.filename}</TableCell>
                        <TableCell>{p.report_file}</TableCell>
                        <TableCell>{(p.emails_sent || []).join(", ") || "-"}</TableCell>
                        <TableCell>{p.last_generated}</TableCell>
                        <TableCell>{p.force ? "true" : "false"}</TableCell>
                      </TableRow>
                    ))}
                    {!runData.processed?.length && (
                      <TableRow>
                        <TableCell colSpan={5} className="text-center text-sm text-muted-foreground py-6">
                          Sem itens processados.
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
