// src/pages/NewReport.tsx
// -----------------------------------------------------------------------------------
// NewReport (alinhado ao Z3Report)
// - Período GLOBAL + frequência define automaticamente o intervalo.
// - Remove date por gráfico; todos os gráficos herdam o período global.
// - Frequência: daily(ontem), weekly(semana anterior seg-dom), monthly(mês anterior), custom.
// - GLPI: somente entidade_id (inicio/fim calculados no backend).
// - Integra services centralizados (relatórios, configs, e-mail).
// - Padrões de segurança: chamadas via /api + Authorization automático.
// -----------------------------------------------------------------------------------

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Select from "react-select";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

import { Button } from "@/components/ui/button";
import {
  Select as ShadcnSelect,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { FileText, Calendar, Save, RefreshCw, UploadCloud, Send } from "lucide-react";

import {
  generatePdfDB,
  createConfig,
  updateConfig as updateConfigSvc,
  emailReportOnDemand,
} from "@/services/reports";

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
interface HostGroup {
  groupid: string;
  name: string;
}
interface Host {
  hostid: string;
  name: string;
  status: string;
}
interface Graph {
  graphid: string;
  name: string;
  width: string;
  height: string;
  graphtype: string;
}
interface SelectedGraph {
  id: string;     // sempre string, normalizamos
  name: string;
  from_time: string; // preenchido pelo período global ao enviar
  to_time: string;   // idem
}
interface ReportPayload {
  hostgroup: { id: string; name: string };
  hosts: Array<{ id: string; name: string; graphs: SelectedGraph[] }>;
  summary: {
    incidents: { enabled: boolean; value: number };
    openProblems: { enabled: boolean; value: any[]; columns: string[] };
    topTriggers: { enabled: boolean; value: any[]; chartType: string };
  };
  emails: string[];
  frequency: string;
  logo_filename: string | null;
  analyst: string;
  comments: string;
  last_generated?: string;
  last_sent_period?: string;
  last_sent?: string;
  itsm?: Record<string, any>;
  glpi?: { entidade_id: number };
}
type SelectOption = { value: string; label: string };
type Frequency = "daily" | "weekly" | "monthly" | "custom";

export default function NewReport() {
  // ---------------------------------------------------------------------------------
  // URL param (?config=arquivo.json) para pré-carregar
  // ---------------------------------------------------------------------------------
  const [searchParams] = useSearchParams();
  const configFilenameFromURL = searchParams.get("config"); // ex.: cliente_x_config_2025-08-15.json

  // ---------------------------------------------------------------------------------
  // Estado principal
  // ---------------------------------------------------------------------------------
  const [hostGroups, setHostGroups] = useState<HostGroup[]>([]);
  const [selectedHostGroup, setSelectedHostGroup] = useState<string>("");
  const [hosts, setHosts] = useState<Host[]>([]);
  const [selectedHosts, setSelectedHosts] = useState<SelectOption[]>([]);
  const [graphs, setGraphs] = useState<Record<string, Graph[]>>({});
  const [selectedGraphs, setSelectedGraphs] = useState<Record<string, SelectedGraph[]>>({});

  const [emails, setEmails] = useState<string>("");
  const [frequency, setFrequency] = useState<Frequency>("weekly");
  const [analyst, setAnalyst] = useState<string>("");
  const [comments, setComments] = useState<string>("");
  const [logoFilename, setLogoFilename] = useState<string>("");

  // GLPI – apenas entidade_id (backend calcula inicio/fim automaticamente)
  const [glpiEntidadeId, setGlpiEntidadeId] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(false);

  // Controle de edição de config existente
  const [currentConfigFilename, setCurrentConfigFilename] = useState<string | null>(null);
  const hasLoadedConfig = useMemo(() => !!currentConfigFilename, [currentConfigFilename]);

  // Prefill de config (após carregar JSON e antes de hosts/graphs)
  const [prefillConfig, setPrefillConfig] = useState<any | null>(null);

  // ---------------------------------------------------------------------------------
  // Período GLOBAL do relatório (um único intervalo)
  // ---------------------------------------------------------------------------------
  const [fromDate, setFromDate] = useState<Date | null>(null);
  const [toDate, setToDate] = useState<Date | null>(null);

  // Helpers de data
  const fmtDateTime = (d: Date) => d.toISOString().slice(0, 19).replace("T", " ");

  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0);
  const endOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);

  const startOfWeek = (d: Date) => {
    const day = d.getDay(); // 0=Dom, 1=Seg, ...
    const diffToMon = (day + 6) % 7; // quantos dias voltar até segunda
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
      // Ontem 00:00:00 → 23:59:59
      const yesterday = new Date(now);
      yesterday.setDate(now.getDate() - 1);
      setFromDate(startOfDay(yesterday));
      setToDate(endOfDay(yesterday));
    } else if (freq === "weekly") {
      // Semana ANTERIOR (seg-dom)
      setFromDate(startOfPrevWeek(now));
      setToDate(endOfPrevWeek(now));
    } else if (freq === "monthly") {
      // Mês ANTERIOR inteiro
      setFromDate(startOfPrevMonth(now));
      setToDate(endOfPrevMonth(now));
    } else {
      // custom: se vazio, aplica últimos 7 dias
      if (!fromDate || !toDate) {
        const end = endOfDay(now);
        const start = new Date(now);
        start.setDate(now.getDate() - 6);
        setFromDate(startOfDay(start));
        setToDate(end);
      }
    }
  };

  // Recalcula datas sempre que mudar a frequência
  useEffect(() => {
    setPeriodByFrequency(frequency);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frequency]);

  // ---------------------------------------------------------------------------------
  // Buscar grupos de hosts (inicial)
  // ---------------------------------------------------------------------------------
  useEffect(() => {
    setLoading(true);
    getJSON<HostGroup[]>("/zabbix/hostgroups")
      .then((data) => setHostGroups(data || []))
      .catch((err) => {
        console.error(err);
        alert("Erro ao buscar grupos de hosts.");
      })
      .finally(() => setLoading(false));
  }, []);

  // ---------------------------------------------------------------------------------
  // Se tiver ?config=..., carrega o JSON e pré-popula campos
  // ---------------------------------------------------------------------------------
  useEffect(() => {
    if (!configFilenameFromURL) return;
    setLoading(true);

    getJSON<any>(`/configs/${encodeURIComponent(configFilenameFromURL)}`)
      .then((cfg) => {
        setCurrentConfigFilename(configFilenameFromURL);

        const hg = cfg.hostgroup || {};
        setSelectedHostGroup(hg.id || hg.groupid || ""); // tolerante a id/groupid
        setEmails((cfg.emails || []).join(", "));
        setFrequency((cfg.frequency as Frequency) || "weekly");
        setAnalyst(cfg.analyst || "");
        setComments(cfg.comments || "");
        setLogoFilename(cfg.logo_filename || "");
        // GLPI (se existir entidade_id)
        setGlpiEntidadeId(cfg?.glpi?.entidade_id ? String(cfg.glpi.entidade_id) : "");

        // Guardamos para aplicar hosts/graphs mais tarde
        setPrefillConfig(cfg);

        // Inferir período global a partir dos gráficos do JSON
        try {
          const ranges: { from: Date; to: Date }[] = [];
          (cfg.hosts || []).forEach((h: any) => {
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
            setPeriodByFrequency((cfg.frequency as Frequency) || "weekly");
          }
        } catch {
          setPeriodByFrequency((cfg.frequency as Frequency) || "weekly");
        }
      })
      .catch((err) => {
        console.error(err);
        alert("Erro ao carregar a configuração.");
      })
      .finally(() => setLoading(false));
  }, [configFilenameFromURL]);

  // ---------------------------------------------------------------------------------
  // Buscar hosts quando um grupo é selecionado
  // ---------------------------------------------------------------------------------
  useEffect(() => {
    async function loadHosts() {
      if (!selectedHostGroup) {
        setHosts([]);
        setSelectedHosts([]);
        setGraphs({});
        setSelectedGraphs({});
        return;
      }
      setLoading(true);
      try {
        const data = await getJSON<Host[]>(`/zabbix/hosts?group_id=${encodeURIComponent(selectedHostGroup)}`);
        setHosts(data);

        // Se vier um config pra pré-preencher, aplica a lista de hosts + graphs
        if (prefillConfig && Array.isArray(prefillConfig.hosts)) {
          const hostOptions: SelectOption[] = [];
          const selectedGraphsTmp: Record<string, SelectedGraph[]> = {};
          for (const h of prefillConfig.hosts) {
            const targetId = String(h.id ?? h.hostid ?? "");
            const existing = data.find((x) => String(x.hostid) === targetId);
            if (!existing) continue;
            hostOptions.push({ value: String(existing.hostid), label: `${existing.name}` });

            // Guarda id/name do gráfico; datas virão do período global no envio
            if (Array.isArray(h.graphs) && h.graphs.length) {
              selectedGraphsTmp[String(existing.hostid)] = h.graphs.map((g: any) => ({
                id: String(g.id ?? g.graphid),
                name: g.name,
                from_time: "",
                to_time: "",
              }));
            }
          }
          setSelectedHosts(hostOptions);
          setSelectedGraphs(selectedGraphsTmp);
          setPrefillConfig(null);
        } else {
          setSelectedHosts([]);
          setGraphs({});
          setSelectedGraphs({});
        }
      } catch (err) {
        console.error(err);
        alert("Erro ao buscar hosts.");
      } finally {
        setLoading(false);
      }
    }
    loadHosts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHostGroup]);

  // ---------------------------------------------------------------------------------
  // Buscar gráficos para cada host selecionado (se ainda não buscados)
  // ---------------------------------------------------------------------------------
  useEffect(() => {
    async function ensureGraphs() {
      for (const { value: hostid } of selectedHosts) {
        if (graphs[hostid]) continue;
        setLoading(true);
        try {
          const data = await getJSON<Graph[]>(`/zabbix/graphs?host_id=${encodeURIComponent(hostid)}`);
          setGraphs((prev) => ({ ...prev, [hostid]: data || [] }));
        } catch (err) {
          console.error(err);
        } finally {
          setLoading(false);
        }
      }
    }
    if (selectedHosts.length) ensureGraphs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedHosts]);

  // ---------------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------------
  const handleHostSelection = (selected: any) => {
    setSelectedHosts(selected || []);
    const allowed = new Set((selected || []).map((s: SelectOption) => s.value));
    setSelectedGraphs((prev) => {
      const next: Record<string, SelectedGraph[]> = {};
      for (const key of Object.keys(prev)) {
        if (allowed.has(key)) next[key] = prev[key];
      }
      return next;
    });
  };

  const handleGraphSelection = (hostid: string, graphid: string) => {
    const gid = String(graphid);
    const graph = graphs[hostid]?.find((g) => String(g.graphid) === gid);
    if (!graph) return;

    setSelectedGraphs((prev) => {
      const hostGraphs = prev[hostid] || [];
      const exists = hostGraphs.some((g) => String(g.id) === gid);
      if (exists) {
        return { ...prev, [hostid]: hostGraphs.filter((g) => String(g.id) !== gid) };
      }
      return {
        ...prev,
        [hostid]: [
          ...hostGraphs,
          {
            id: gid,
            name: graph.name,
            from_time: "",
            to_time: "",
          },
        ],
      };
    });
  };

  // ---------------------------------------------------------------------------------
  // Builder do payload (usa PERÍODO GLOBAL para todos os gráficos)
  // ---------------------------------------------------------------------------------
  const buildPayload = (): ReportPayload | null => {
    if (!selectedHostGroup || selectedHosts.length === 0) {
      alert("Selecione um grupo e pelo menos um host.");
      return null;
    }
    if (!fromDate || !toDate) {
      alert("Defina o período do relatório (De / Até).");
      return null;
    }
    const selectedGroup = hostGroups.find((g) => String(g.groupid) === String(selectedHostGroup));
    if (!selectedGroup) {
      alert("Grupo inválido.");
      return null;
    }

    const from_time = fmtDateTime(fromDate);
    const to_time = fmtDateTime(toDate);

    const payload: ReportPayload = {
      hostgroup: { id: String(selectedGroup.groupid), name: selectedGroup.name },
      hosts: selectedHosts.map(({ value: hostid }) => ({
        id: String(hostid),
        name: hosts.find((h) => String(h.hostid) === String(hostid))?.name || "",
        graphs: (selectedGraphs[String(hostid)] || []).map((g) => ({
          ...g,
          id: String(g.id),
          from_time,
          to_time,
        })),
      })),
      summary: {
        incidents: { enabled: false, value: 0 },
        openProblems: { enabled: false, value: [], columns: ["name", "severity", "tags", "clock"] },
        topTriggers: { enabled: false, value: [], chartType: "bar" },
      },
      emails: emails.split(",").map((e) => e.trim()).filter(Boolean),
      frequency,
      logo_filename: logoFilename || null,
      analyst: analyst || "",
      comments: comments || "",
      last_generated: "",
      last_sent_period: "",
      last_sent: "",
      ...(glpiEntidadeId ? { glpi: { entidade_id: Number(glpiEntidadeId) } } : {}),
    };
    return payload;
  };

  // ---------------------------------------------------------------------------------
  // Ações
  // ---------------------------------------------------------------------------------
  const handleCreateReport = async () => {
    const payload = buildPayload();
    if (!payload) return;

    try {
      setLoading(true);
      const blob = await generatePdfDB(payload);
      // Se o service não devolver o filename, usamos um fallback seguro
      const filename = "relatorio.pdf";
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert("Erro ao criar/baixar o relatório.");
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async () => {
    const payload = buildPayload();
    if (!payload) return;

    const recips = payload.emails;
    if (!recips.length) {
      alert("Informe pelo menos um e-mail nos destinatários.");
      return;
    }
    try {
      setLoading(true);
      await emailReportOnDemand(payload, recips);
      alert("Relatório gerado e enviado por e-mail com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Falha ao enviar relatório por e-mail.");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConfig = async () => {
    const payload = buildPayload();
    if (!payload) return;

    try {
      setLoading(true);
      const data = await createConfig(payload);
      setCurrentConfigFilename(data?.filename || null);
      alert("Configuração salva com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao salvar configuração.");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateConfig = async () => {
    if (!currentConfigFilename) {
      alert("Nenhum arquivo de configuração carregado.");
      return;
    }
    const payload = buildPayload();
    if (!payload) return;

    try {
      setLoading(true);
      await updateConfigSvc(currentConfigFilename, payload);
      alert("Configuração atualizada com sucesso!");
    } catch (err) {
      console.error(err);
      alert("Erro ao atualizar configuração.");
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------------------------------
  // UI
  // ---------------------------------------------------------------------------------
  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header da página */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Novo Relatório / Editar Configuração</h1>
        <div className="flex items-center gap-2">
          {hasLoadedConfig ? (
            <span className="text-xs text-muted-foreground">
              Editando: <code>{currentConfigFilename}</code>
            </span>
          ) : (
            <span className="text-xs text-muted-foreground">Sem arquivo carregado</span>
          )}
          <Button variant="outline" onClick={() => window.location.reload()} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Recarregar
          </Button>
        </div>
      </div>

      {/* Cabeçalho com grupo, frequência e período global */}
      <Card>
        <CardContent className="grid md:grid-cols-2 gap-6 pt-6">
          {/* Grupo de Hosts */}
          <div className="space-y-2">
            <Label>Grupo de Hosts</Label>
            <ShadcnSelect
              value={selectedHostGroup || undefined}
              onValueChange={setSelectedHostGroup}
              disabled={loading}
            >
              <SelectTrigger><SelectValue placeholder="Selecione um grupo" /></SelectTrigger>
              <SelectContent>
                {hostGroups.map((group) => (
                  <SelectItem key={group.groupid} value={group.groupid}>
                    {group.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </ShadcnSelect>
          </div>

          {/* Frequência */}
          <div className="space-y-2">
            <Label>Frequência</Label>
            <ShadcnSelect
              value={frequency}
              onValueChange={(v: Frequency) => setFrequency(v)}
              disabled={loading}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Diário (ontem)</SelectItem>
                <SelectItem value="weekly">Semanal (semana anterior)</SelectItem>
                <SelectItem value="monthly">Mensal (mês anterior)</SelectItem>
                <SelectItem value="custom">Custom</SelectItem>
              </SelectContent>
            </ShadcnSelect>
          </div>

          {/* Período global - De */}
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
            <div className="text-xs text-muted-foreground">
              O período é aplicado a todos os gráficos selecionados.
            </div>
          </div>

          {/* Período global - Até */}
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

          {/* E-mails */}
          <div className="space-y-2">
            <Label>E-mails (separados por vírgula)</Label>
            <Input
              value={emails}
              onChange={(e) => setEmails(e.target.value)}
              placeholder="ex.: exemplo@dominio.com, outro@dominio.com"
              disabled={loading}
            />
          </div>

          {/* Analista */}
          <div className="space-y-2">
            <Label>Analista</Label>
            <Input
              value={analyst}
              onChange={(e) => setAnalyst(e.target.value)}
              placeholder="Nome do analista"
              disabled={loading}
            />
          </div>

          {/* Comentários */}
          <div className="space-y-2">
            <Label>Comentários</Label>
            <Input
              value={comments}
              onChange={(e) => setComments(e.target.value)}
              placeholder="Comentários opcionais"
              disabled={loading}
            />
          </div>

          {/* Logo */}
          <div className="space-y-2">
            <Label>Logo (opcional) — arquivo em configs/logos/</Label>
            <Input
              value={logoFilename}
              onChange={(e) => setLogoFilename(e.target.value)}
              placeholder="ex.: logo_cliente.png"
              disabled={loading}
            />
          </div>

          {/* GLPI – somente entidade_id */}
          <div className="space-y-2">
            <Label>GLPI — Entidade ID (opcional)</Label>
            <Input
              value={glpiEntidadeId}
              onChange={(e) => setGlpiEntidadeId(e.target.value.replace(/\D/g, ""))}
              placeholder="ex.: 68"
              disabled={loading}
            />
            <div className="text-xs text-muted-foreground">
              Se informado, o backend calcula automaticamente o período do GLPI.
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Hosts e seleção de gráficos */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          <div>
            <Label>Hosts</Label>
            <Select
              isMulti
              options={hosts.map((host) => ({
                value: String(host.hostid),
                label: `${host.name} ${host.status === "0" ? "(Ativo)" : "(Inativo)"}`,
              }))}
              value={selectedHosts}
              onChange={handleHostSelection}
              placeholder="Selecione hosts"
              isDisabled={loading || !selectedHostGroup}
              className="react-select-container"
              classNamePrefix="react-select"
            />
          </div>

          <div>
            <Label>Gráficos</Label>
            <div className="space-y-6">
              {selectedHosts.map(({ value: hostid, label }) => (
                <div key={hostid} className="rounded-md border p-3">
                  <div className="font-medium mb-2">{label}</div>
                  <div className="space-y-2">
                    {graphs[hostid]?.map((graph) => {
                      const gid = String(graph.graphid);
                      const checked = !!selectedGraphs[hostid]?.some((g) => String(g.id) === gid);
                      return (
                        <label key={gid} className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => handleGraphSelection(hostid, gid)}
                            disabled={loading}
                          />
                          <span>{graph.name}</span>
                        </label>
                      );
                    })}
                    {!graphs[hostid]?.length && (
                      <div className="text-sm text-muted-foreground">
                        Nenhum gráfico encontrado para este host.
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {!selectedHosts.length && (
                <div className="text-sm text-muted-foreground">
                  Selecione ao menos um host para listar gráficos.
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Ações */}
      <div className="flex flex-wrap gap-2">
        <Button
          className="btn-ruach-primary"
          onClick={handleCreateReport}
          disabled={loading || selectedHosts.length === 0}
        >
          <FileText className="mr-2 h-4 w-4" />
          Gerar PDF
        </Button>

        <Button variant="outline" onClick={handleSaveConfig} disabled={loading || selectedHosts.length === 0}>
          <UploadCloud className="mr-2 h-4 w-4" />
          Salvar como Config
        </Button>

        <Button variant="secondary" onClick={handleUpdateConfig} disabled={loading || !hasLoadedConfig}>
          <Save className="mr-2 h-4 w-4" />
          Atualizar Config
        </Button>

        <Button variant="outline" onClick={handleSendEmail} disabled={loading || selectedHosts.length === 0}>
          <Send className="mr-2 h-4 w-4" />
          Enviar por E-mail
        </Button>
      </div>
    </div>
  );
}
