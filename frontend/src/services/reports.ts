// src/services/reports.ts
const API = "http://localhost:8000";

export async function generatePdfDB(payload: any): Promise<Blob> {
  const r = await fetch(`${API}/reports/pdf/db`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Erro ao gerar PDF DB (${r.status})`);
  return await r.blob();
}

export async function emailReportOnDemand(data: any, recipient: string | string[]) {
  const r = await fetch(`${API}/reports/pdf/email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ data, recipient }),
  });
  if (!r.ok) throw new Error(`Erro ao enviar e-mail (${r.status})`);
  return await r.json();
}

export async function listConfigs(): Promise<string[]> {
  const r = await fetch(`${API}/configs/`);
  if (!r.ok) throw new Error(`Erro ao listar configs (${r.status})`);
  return await r.json();
}

export async function getConfig(filename: string) {
  const r = await fetch(`${API}/configs/${encodeURIComponent(filename)}`);
  if (!r.ok) throw new Error(`Erro ao carregar config (${r.status})`);
  return await r.json();
}

export async function createConfig(payload: any) {
  const r = await fetch(`${API}/configs/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Erro ao salvar config (${r.status})`);
  return await r.json();
}

export async function updateConfig(filename: string, payload: any) {
  const r = await fetch(`${API}/configs/${encodeURIComponent(filename)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Erro ao atualizar config (${r.status})`);
  return await r.json();
}

export async function runScheduled(force = false) {
  const r = await fetch(`${API}/reports/scheduled/run${force ? "?force=true" : ""}`, { method: "POST" });
  if (!r.ok) throw new Error(`Erro ao executar agendados (${r.status})`);
  return await r.json();
}

export async function emailExistingFile(filename: string, payload: {
  emails: string | string[];
  hostgroup_name?: string;
  periodo?: string;
  analyst?: string;
  comments?: string;
  logo_filename?: string;
}) {
  const r = await fetch(`${API}/reports/files/${encodeURIComponent(filename)}/email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) throw new Error(`Erro ao enviar PDF existente (${r.status})`);
  return await r.json();
}

export async function deleteFile(filename: string) {
  const r = await fetch(`${API}/reports/files/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!r.ok) {
    if (r.status === 423) {
      const j = await r.json().catch(() => ({}));
      throw new Error(j.detail || "Arquivo em uso/sem permissão para exclusão.");
    }
    throw new Error(`Erro ao excluir (${r.status})`);
  }
  return await r.json();
}
