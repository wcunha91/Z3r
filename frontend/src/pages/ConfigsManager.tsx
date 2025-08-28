// src/pages/ConfigsManager.tsx
// ----------------------------------------------------------------------------------
// Gerenciador de Configurações (configs/*.json) alinhado ao NewReport:
// - Frequência (daily/weekly/monthly/custom) + Período GLOBAL (De/Até)
// - Ao gerar PDF ou enviar e-mail, injeta o período global em todos os gráficos
// - GLPI: editar apenas entidade_id; inicio/fim são calculados no backend
// - Listar, visualizar, baixar, editar, duplicar, excluir
// - Abrir para edição avançada: /reports/new?config=<filename>
// - Ajustes: base da API padronizada (/api) e Authorization automático
// ----------------------------------------------------------------------------------

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from "@/components/ui/dialog";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select as ShadcnSelect, SelectContent, SelectItem, SelectTrigger, SelectValue
} from "@/components/ui/select";

import {
  Loader2, FileCog, Eye, Download, Trash2, Copy, Save, Send, FileText, RefreshCw, Wrench, ExternalLink, Calendar, Shield
} from "lucide-react";

// ========================= Helpers compactos de API ========================= //
// Sempre chame a API via /api. Em dev o Vite faz proxy; em prod o reverse-proxy atende.
const API_BASE = "/api";
function authHeaders() {
  const t = localStorage.getItem("auth_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}
async function getJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...authHeaders(), ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${init?.method ?? "GET"} ${path} falhou (${res.status}): ${txt}`);
  }
  return res.json() as Promise<T>;
}

// =============================== Tipagens ================================== //
type ConfigListItem = string; // backend retorna apenas o nome do arquivo
type ConfigObject = Record<string, any>;
type Frequency = "daily" | "weekly" | "monthly" | "custom";

export default function ConfigsManager() {
  const navigate = useNavigate();

  // -----------------------------
  // Estados principais
  // -----------------------------
  const [loading, setLoading] = useState(false);
  const [configs, setConfigs] = useState<ConfigListItem[]>([]);
  const [query, setQuery] = useState("");
  const [selectedFilename, setSelectedFilename] = useState<string | null>(null);
  const [selectedContent, setSelectedContent] = useState<ConfigObject | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // -----------------------------
  // Período GLOBAL + frequência (alinhado ao NewReport)
  // -----------------------------
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [fromDate, setFromDate] = useState<Date | null>(null);
  const [toDate, setToDate] = useState<Date | null>(null);

  // Helpers de data
  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0);
  const endOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);
  const fmtDateTime = (d: Date) => d.toISOString().slice(0, 19).replace("T", " ");

  const startOfWeek = (d: Date) => {
    const day = d.getDay(); // 0=Dom, 1=Seg...
    const diffToMon = (day + 6) % 7;
    const dt = new Date(d);
    dt.setDate(d.getDate() - diffToMon);
    return startOfDay(dt);
  };
  const endOfWeek = (d: Date) => {
    const s = startOfWeek(d);
    const e = new Date(s);
    e.setDate(s.getDate() + 6);
    return endOfDay(e);
  };
  const startOfPrevWeek = (d: Date) => {
    const s = startOfWeek(d);
    const prev = new Date(s);
    prev.setDate(s.getDate() - 7);
    return startOfDay(prev);
  };
  const endOfPrevWeek = (d: Date) => {
    const s = startOfPrevWeek(d);
    const e = new Date(s);
    e.setDate(s.getDate() + 6);
    return endOfDay(e);
  };
  const startOfPrevMonth = (d: Date) => {
    const firstOfThis = new Date(d.getFullYear(), d.getMonth(), 1);
    const lastOfPrev = new Date(firstOfThis.getTime() - 86400000);
    return new Date(lastOfPrev.getFullYear(), lastOfPrev.getMonth(), 1, 0, 0, 0);
  };
  const endOfPrevMonth = (d: Date) => {
    const firstOfThis = new Date(d.getFullYear(), d.getMonth(), 1);
    const lastOfPrev = new Date(firstOfThis.getTime() - 86400000);
    return endOfDay(lastOfPrev);
  };

  const setPeriodByFrequency = (freq: Frequency) => {
    const now = new Date();
    if (freq === "daily") {
      const y = new Date(now);
      y.setDate(now.getDate() - 1);
      setFromDate(startOfDay(y));
      setToDate(endOfDay(y));
    } else if (freq === "weekly") {
      setFromDate(startOfPrevWeek(now));
      setToDate(endOfPrevWeek(now));
    } else if (freq === "monthly") {
      setFromDate(startOfPrevMonth(now));
      setToDate(endOfPrevMonth(now));
    } else {
      // custom: se ainda não definido, define últimos 7 dias
      if (!fromDate || !toDate) {
        const end = endOfDay(now);
        const start = new Date(now);
        start.setDate(now.getDate() - 6);
        setFromDate(startOfDay(start));
        setToDate(end);
      }
    }
  };

  useEffect(() => {
    setPeriodByFrequency(frequency);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frequency]);

  // -----------------------------
  // GLPI (somente entidade_id)
  // -----------------------------
  const glpiEntidadeId: string = String(selectedContent?.glpi?.entidade_id ?? "");

  const setGlpiEntidadeId = (val: string) => {
    if (!selectedContent) return;
    const next = {
      ...selectedContent,
      glpi: { ...(selectedContent.glpi ?? {}), entidade_id: val ? Number(val) : undefined },
    };
    // Se vazio, remove glpi
    if (!val) delete (next as any).glpi;
    setSelectedContent(next);
  };

  async function saveGlpiEntidadeId() {
    if (!selectedFilename || !selectedContent) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/configs/${encodeURIComponent(selectedFilename)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(selectedContent),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao salvar GLPI (${res.status}): ${txt}`);
      }
      alert("GLPI atualizado com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar GLPI.");
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------
  // Modais
  // -----------------------------
  // Editar JSON
  const [editOpen, setEditOpen] = useState(false);
  const [editJsonText, setEditJsonText] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);

  // Duplicar
  const [dupOpen, setDupOpen] = useState(false);
  const [dupSaving, setDupSaving] = useState(false);
  const [dupNewHostgroup, setDupNewHostgroup] = useState("");

  // Enviar e-mail
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [emailRecipients, setEmailRecipients] = useState(""); // vírgula-separado
  const [emailAnalyst, setEmailAnalyst] = useState("");
  const [emailComments, setEmailComments] = useState("");
  const [emailLogoFilename, setEmailLogoFilename] = useState("");
  const [emailPeriod, setEmailPeriod] = useState(""); // "YYYY-MM-DD a YYYY-MM-DD" (apenas visual)

  // -----------------------------
  // Effects
  // -----------------------------
  useEffect(() => {
    loadList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  useEffect(() => {
    if (selectedFilename) {
      loadConfig(selectedFilename);
    } else {
      setSelectedContent(null);
    }
  }, [selectedFilename]);

  // -----------------------------
  // Fetchers
  // -----------------------------
  async function loadList() {
    try {
      setLoading(true);
      const data = await getJSON<ConfigListItem[]>("/configs/");
      setConfigs(data);
      if (selectedFilename && !data.includes(selectedFilename)) {
        setSelectedFilename(null);
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao listar configurações.");
    } finally {
      setLoading(false);
    }
  }

  async function loadConfig(filename: string) {
    try {
      const data = await getJSON<ConfigObject>(`/configs/${encodeURIComponent(filename)}`);
      setSelectedContent(data);

      // Ajusta frequência (se vier inválida, cai em custom)
      const f = (data.frequency as Frequency) || "weekly";
      setFrequency(["daily", "weekly", "monthly", "custom"].includes(f) ? (f as Frequency) : "custom");

      // Inferir período a partir dos gráficos
      try {
        const ranges: { from: Date; to: Date }[] = [];
        (data.hosts || []).forEach((h: any) => {
          (h.graphs || []).forEach((g: any) => {
            if (g.from_time && g.to_time) {
              const f = new Date(String(g.from_time).replace(" ", "T"));
              const t = new Date(String(g.to_time).replace(" ", "T"));
              if (!isNaN(f.getTime()) && !isNaN(t.getTime())) {
                ranges.push({ from: f, to: t });
              }
            }
          });
        });
        if (ranges.length) {
          const minF = new Date(Math.min(...ranges.map((r) => r.from.getTime())));
          const maxT = new Date(Math.max(...ranges.map((r) => r.to.getTime())));
          setFromDate(minF);
          setToDate(maxT);
        } else {
          // caso não tenha datas, deixa a frequência definir
          setPeriodByFrequency(f);
        }
      } catch {
        setPeriodByFrequency(f);
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao carregar a configuração.");
    }
  }

  // -----------------------------
  // Ações: Baixar config (client-side)
  // -----------------------------
  function downloadConfigClientSide(filename: string, content: ConfigObject) {
    try {
      const blob = new Blob([JSON.stringify(content, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Erro ao preparar download da configuração.");
    }
  }

  // -----------------------------
  // Ações: Editar & Salvar (JSON)
  // -----------------------------
  function openEditModal() {
    if (!selectedContent || !selectedFilename) return;
    setEditJsonText(JSON.stringify(selectedContent, null, 2));
    setEditOpen(true);
  }

  async function saveEdit() {
    if (!selectedFilename) return;
    let parsed: any;
    try {
      parsed = JSON.parse(editJsonText);
    } catch {
      alert("JSON inválido. Verifique a formatação.");
      return;
    }
    try {
      setSavingEdit(true);
      const res = await fetch(`${API_BASE}/configs/${encodeURIComponent(selectedFilename)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(parsed),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao salvar (${res.status}): ${txt}`);
      }
      setEditOpen(false);
      await loadConfig(selectedFilename);
      alert("Configuração atualizada com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar a configuração.");
    } finally {
      setSavingEdit(false);
    }
  }

  // -----------------------------
  // Ações: Duplicar (POST /configs/)
  // -----------------------------
  function openDuplicateModal() {
    if (!selectedContent) return;
    setDupNewHostgroup("");
    setDupOpen(true);
  }

  async function doDuplicate() {
    if (!selectedContent) return;
    if (!dupNewHostgroup.trim()) {
      alert("Informe o novo nome do hostgroup para a cópia.");
      return;
    }
    try {
      setDupSaving(true);
      const copyPayload = {
        ...selectedContent,
        hostgroup: {
          ...(selectedContent.hostgroup || {}),
          name: dupNewHostgroup.trim(),
        },
      };
      const res = await fetch(`${API_BASE}/configs/`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(copyPayload),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao duplicar (${res.status}): ${txt}`);
      }
      setDupOpen(false);
      setRefreshKey((k) => k + 1);
      alert("Configuração duplicada com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao duplicar configuração.");
    } finally {
      setDupSaving(false);
    }
  }

  // -----------------------------
  // Ações: Excluir
  // -----------------------------
  async function deleteConfig(filename: string) {
    if (!confirm(`Excluir a configuração "${filename}"?`)) return;
    try {
      setLoading(true);
      const res = await fetch(`${API_BASE}/configs/${encodeURIComponent(filename)}`, {
        method: "DELETE",
        headers: { ...authHeaders() },
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao excluir (${res.status}): ${txt}`);
      }
      if (selectedFilename === filename) {
        setSelectedFilename(null);
        setSelectedContent(null);
      }
      setRefreshKey((k) => k + 1);
    } catch (err) {
      console.error(err);
      alert("Erro ao excluir configuração.");
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------
  // Injeção do PERÍODO GLOBAL na config antes de ações
  // -----------------------------
  function applyGlobalPeriodToConfig(cfg: ConfigObject): ConfigObject {
    if (!fromDate || !toDate) return cfg;
    const from_time = fmtDateTime(fromDate);
    const to_time = fmtDateTime(toDate);
    const cloned = JSON.parse(JSON.stringify(cfg || {}));

    (cloned.hosts || []).forEach((h: any) => {
      (h.graphs || []).forEach((g: any) => {
        g.from_time = from_time;
        g.to_time = to_time;
      });
    });

    // mantém frequency escolhida na UI
    cloned.frequency = frequency;

    // GLPI: se houver entidade_id, removemos inicio/fim para deixar backend calcular
    if (cloned.glpi && cloned.glpi.entidade_id) {
      delete cloned.glpi.inicio;
      delete cloned.glpi.fim;
    }
    return cloned;
  }

  // -----------------------------
  // Ações: Gerar & Baixar PDF (POST /reports/pdf/download)
  // -----------------------------
  async function generateAndDownloadPdfFromConfig(cfg: ConfigObject) {
    if (!selectedContent) return;
    if (!fromDate || !toDate) {
      alert("Defina o período (De/Até) para gerar o relatório.");
      return;
    }
    try {
      setLoading(true);
      const payload = applyGlobalPeriodToConfig(cfg);
      const res = await fetch(`${API_BASE}/reports/pdf/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`Falha ao gerar PDF (${res.status}): ${txt}`);
      }
      const blob = await res.blob();
      const cd = res.headers.get("Content-Disposition") || "";
      const match = /filename\*?=(?:UTF-8'')?("?)([^";]+)\1/.exec(cd);
      const filename = match ? decodeURIComponent(match[2]) : "relatorio.pdf";

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Erro ao gerar/baixar o PDF.");
    } finally {
      setLoading(false);
    }
  }

  // -----------------------------
  // Ações: Enviar por e-mail (POST /reports/pdf/email)
  // -----------------------------
  function openEmailModal() {
    if (!selectedContent) return;
    setEmailRecipients((selectedContent.emails || []).join(", "));
    setEmailAnalyst(selectedContent.analyst || "");
    setEmailComments(selectedContent.comments || "");
    setEmailLogoFilename(selectedContent.logo_filename || "");

    // preenchimento sugerido do texto do período
    if (fromDate && toDate) {
      const f = fmtDateTime(fromDate).slice(0, 10);
      const t = fmtDateTime(toDate).slice(0, 10);
      setEmailPeriod(`${f} a ${t}`);
    } else {
      setEmailPeriod("");
    }
    setEmailOpen(true);
  }

  async function sendEmailFromConfig(cfg: ConfigObject) {
    const recipients = emailRecipients
      .split(",")
      .map((e) => e.trim())
      .filter(Boolean);

    if (recipients.length === 0) {
      alert("Informe ao menos um e-mail.");
      return;
    }
    if (!fromDate || !toDate) {
      alert("Defina o período (De/Até) antes de enviar.");
      return;
    }

    try {
      setEmailSending(true);
      const payloadCfg = applyGlobalPeriodToConfig({
        ...cfg,
        analyst: emailAnalyst || cfg.analyst,
        comments: emailComments || cfg.comments,
        logo_filename: emailLogoFilename || cfg.logo_filename,
      });

      const body = {
        data: payloadCfg,
        recipient: recipients,
      };

      const res = await fetch(`${API_BASE}/reports/pdf/email`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
      });
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
  }

  // -----------------------------
  // Filtro por nome
  // -----------------------------
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return configs;
    return configs.filter((name) => name.toLowerCase().includes(q));
  }, [configs, query]);

  // -----------------------------
  // Render
  // -----------------------------
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileCog className="h-6 w-6" />
          Configurações Salvas
        </h1>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => setRefreshKey((k) => k + 1)} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* Filtros simples */}
      <Card>
        <CardHeader>
          <CardTitle>Filtros</CardTitle>
        </CardHeader>
        <CardContent className="grid md:grid-cols-3 gap-4">
          <div className="col-span-1">
            <Label>Pesquisar por nome do arquivo</Label>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="ex.: _config_2025-08-15.json"
              disabled={loading}
            />
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LISTAGEM */}
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
                    <TableHead className="w-[520px]">Ações</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((name) => (
                    <TableRow key={name} className={selectedFilename === name ? "bg-accent/10" : ""}>
                      <TableCell className="font-medium">{name}</TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-2">
                          <Button variant="secondary" onClick={() => setSelectedFilename(name)}>
                            <Eye className="mr-2 h-4 w-4" />
                            Visualizar
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => {
                              setSelectedFilename(name);
                              loadConfig(name).then(() => {
                                setTimeout(() => {
                                  if (selectedContent) downloadConfigClientSide(name, selectedContent);
                                }, 50);
                              });
                            }}
                          >
                            <Download className="mr-2 h-4 w-4" />
                            Baixar
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => {
                              setSelectedFilename(name);
                              loadConfig(name).then(() => openEditModal());
                            }}
                          >
                            <Wrench className="mr-2 h-4 w-4" />
                            Editar JSON
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => {
                              setSelectedFilename(name);
                              loadConfig(name).then(() => openDuplicateModal());
                            }}
                          >
                            <Copy className="mr-2 h-4 w-4" />
                            Duplicar
                          </Button>
                          <Button variant="destructive" onClick={() => deleteConfig(name)}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            Excluir
                          </Button>
                          <Button
                            variant="outline"
                            onClick={() => navigate(`/reports/new?config=${encodeURIComponent(name)}`)}
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Editar no NewReport
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!filtered.length && (
                    <TableRow>
                      <TableCell colSpan={2} className="text-center text-sm text-muted-foreground py-6">
                        Nenhum arquivo encontrado.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        {/* VISUALIZAÇÃO + CONTROLES DE PERÍODO/FREQ + GLPI + AÇÕES */}
        <Card className="min-h-[560px]">
          <CardHeader>
            <CardTitle>Conteúdo & Período</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedFilename ? (
              <div className="text-sm text-muted-foreground">Selecione um arquivo para visualizar aqui.</div>
            ) : !selectedContent ? (
              <div className="text-sm text-muted-foreground">Carregando conteúdo...</div>
            ) : (
              <>
                <div className="text-xs text-muted-foreground">{selectedFilename}</div>

                {/* Frequência + Período global */}
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Frequência</Label>
                    <ShadcnSelect value={frequency} onValueChange={(v: Frequency) => setFrequency(v)} disabled={loading}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="daily">Diário (ontem)</SelectItem>
                        <SelectItem value="weekly">Semanal (semana anterior)</SelectItem>
                        <SelectItem value="monthly">Mensal (mês anterior)</SelectItem>
                        <SelectItem value="custom">Custom</SelectItem>
                      </SelectContent>
                    </ShadcnSelect>
                  </div>

                  <div className="space-y-2">
                    <Label>De</Label>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      <DatePicker
                        selected={fromDate || undefined}
                        onChange={(d) => setFromDate(d)}
                        showTimeSelect
                        dateFormat="yyyy-MM-dd HH:mm:ss"
                        className="input-ruach text-sm"
                        disabled={loading}
                        placeholderText="yyyy-MM-dd HH:mm:ss"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>Até</Label>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      <DatePicker
                        selected={toDate || undefined}
                        onChange={(d) => setToDate(d)}
                        showTimeSelect
                        dateFormat="yyyy-MM-dd HH:mm:ss"
                        className="input-ruach text-sm"
                        disabled={loading}
                        placeholderText="yyyy-MM-dd HH:mm:ss"
                      />
                    </div>
                  </div>
                </div>

                {/* Painel GLPI - apenas entidade_id (inicio/fim calculado no backend) */}
                <div className="rounded-md border p-3 space-y-3">
                  <div className="flex items-center gap-2">
                    <Shield className="h-4 w-4" />
                    <div className="font-medium">GLPI</div>
                  </div>
                  <div className="grid md:grid-cols-3 gap-3">
                    <div className="space-y-2 md:col-span-1">
                      <Label>Entidade ID (obrigatório para usar GLPI)</Label>
                      <Input
                        type="number"
                        placeholder="ex.: 68"
                        value={glpiEntidadeId}
                        onChange={(e) => setGlpiEntidadeId(e.target.value)}
                      />
                      <div className="text-xs text-muted-foreground">
                        O período do GLPI é <b>calculado automaticamente</b> no backend:
                        mensal = mês anterior; semanal = 1ª semana → mês anterior, demais → semana.
                      </div>
                    </div>
                    <div className="flex items-end gap-2 md:col-span-2">
                      <Button variant="outline" onClick={saveGlpiEntidadeId} disabled={!selectedFilename || loading}>
                        <Save className="mr-2 h-4 w-4" />
                        Salvar GLPI
                      </Button>
                    </div>
                  </div>
                </div>

                <pre className="text-sm p-3 rounded-md border overflow-auto max-h-[40vh] bg-background">
                  {JSON.stringify(selectedContent, null, 2)}
                </pre>

                <div className="flex flex-wrap gap-2">
                  <Button onClick={() => generateAndDownloadPdfFromConfig(selectedContent!)}>
                    <FileText className="mr-2 h-4 w-4" />
                    Gerar & Baixar PDF
                  </Button>
                  <Button variant="outline" onClick={openEmailModal}>
                    <Send className="mr-2 h-4 w-4" />
                    Enviar por e-mail
                  </Button>
                  <Button variant="outline" onClick={openEditModal}>
                    <Wrench className="mr-2 h-4 w-4" />
                    Editar & Salvar JSON
                  </Button>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Modal: Editar JSON */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-[800px]">
          <DialogHeader>
            <DialogTitle>Editar configuração</DialogTitle>
            <DialogDescription>
              Edite o JSON da configuração. Campos obrigatórios: <code>hostgroup</code>, <code>hosts</code>.
              <br />
              Dica: se usar GLPI, mantenha apenas <code>glpi.entidade_id</code> (sem <code>inicio</code>/<code>fim</code>).
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={editJsonText}
            onChange={(e) => setEditJsonText(e.target.value)}
            className="min-h-[380px] font-mono text-xs"
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)} disabled={savingEdit}>Cancelar</Button>
            <Button onClick={saveEdit} disabled={savingEdit}>
              {savingEdit ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
              Salvar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Duplicar */}
      <Dialog open={dupOpen} onOpenChange={setDupOpen}>
        <DialogContent className="sm:max-w-[560px]">
          <DialogHeader>
            <DialogTitle>Duplicar configuração</DialogTitle>
            <DialogDescription>
              Informe o novo <code>hostgroup.name</code> para salvar uma cópia.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-2">
            <Label>Novo hostgroup</Label>
            <Input
              placeholder="ex.: Cliente_XYZ"
              value={dupNewHostgroup}
              onChange={(e) => setDupNewHostgroup(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDupOpen(false)} disabled={dupSaving}>Cancelar</Button>
            <Button onClick={doDuplicate} disabled={dupSaving}>
              {dupSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Copy className="mr-2 h-4 w-4" />}
              Duplicar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal: Enviar e-mail */}
      <Dialog open={emailOpen} onOpenChange={setEmailOpen}>
        <DialogContent className="sm:max-w-[620px]">
          <DialogHeader>
            <DialogTitle>Enviar relatório por e-mail</DialogTitle>
            <DialogDescription>
              Gera o PDF a partir desta config (com o período global definido) e envia aos destinatários informados.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4">
            <div className="grid gap-2">
              <Label>E-mails (separados por vírgula) *</Label>
              <Input
                placeholder="ex.: pessoa@dominio.com, outro@dominio.com"
                value={emailRecipients}
                onChange={(e) => setEmailRecipients(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Analista (opcional)</Label>
              <Input
                placeholder="Nome do analista"
                value={emailAnalyst}
                onChange={(e) => setEmailAnalyst(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Comentários (opcional)</Label>
              <Textarea
                placeholder="Mensagem adicional no corpo do e-mail"
                value={emailComments}
                onChange={(e) => setEmailComments(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Logo (opcional) — arquivo em configs/logos/</Label>
              <Input
                placeholder="ex.: logo_cliente.png"
                value={emailLogoFilename}
                onChange={(e) => setEmailLogoFilename(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label>Período (opcional — texto no corpo/assunto)</Label>
              <Input
                placeholder="YYYY-MM-DD a YYYY-MM-DD"
                value={emailPeriod}
                onChange={(e) => setEmailPeriod(e.target.value)}
              />
              <div className="text-xs text-muted-foreground">
                Obs.: o período <b>aplicado nos gráficos</b> é o definido em <b>De/Até</b> (acima). Este campo é apenas textual.
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEmailOpen(false)} disabled={emailSending}>
              Cancelar
            </Button>
            <Button
              onClick={() => selectedContent && sendEmailFromConfig(selectedContent)}
              disabled={emailSending}
            >
              {emailSending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Send className="mr-2 h-4 w-4" />}
              Enviar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
