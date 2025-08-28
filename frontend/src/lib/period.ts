// src/lib/period.ts
export type Period = { from: string; to: string };

/** YYYY-MM-DD HH:mm:ss (local) */
function fmt(d: Date, endOfDay = false) {
  const dd = new Date(d);
  if (endOfDay) dd.setHours(23, 59, 59, 0);
  const yyyy = dd.getFullYear();
  const mm = String(dd.getMonth() + 1).padStart(2, "0");
  const day = String(dd.getDate()).padStart(2, "0");
  const hh = String(dd.getHours()).padStart(2, "0");
  const mi = String(dd.getMinutes()).padStart(2, "0");
  const ss = String(dd.getSeconds()).padStart(2, "0");
  return `${yyyy}-${mm}-${day} ${hh}:${mi}:${ss}`;
}

/** Semana anterior (seg→dom) */
export function lastWeek(): Period {
  const now = new Date();
  const dow = (now.getDay() + 6) % 7; // 0=seg
  const startThisWeek = new Date(now);
  startThisWeek.setDate(now.getDate() - dow);
  startThisWeek.setHours(0, 0, 0, 0);

  const startPrev = new Date(startThisWeek);
  startPrev.setDate(startThisWeek.getDate() - 7);

  const endPrev = new Date(startPrev);
  endPrev.setDate(startPrev.getDate() + 6);
  endPrev.setHours(23, 59, 59, 0);

  return { from: fmt(startPrev), to: fmt(endPrev, true) };
}

/** Mês anterior inteiro */
export function lastMonth(): Period {
  const now = new Date();
  const firstThis = new Date(now.getFullYear(), now.getMonth(), 1);
  const lastPrev = new Date(firstThis.getTime() - 86400000);

  const firstPrev = new Date(lastPrev.getFullYear(), lastPrev.getMonth(), 1);
  const lastDay = new Date(lastPrev.getFullYear(), lastPrev.getMonth() + 1, 0); // último dia

  return { from: fmt(firstPrev), to: fmt(lastDay, true) };
}

export function periodForFrequency(freq: string): Period {
  if (freq === "weekly") return lastWeek();
  if (freq === "monthly") return lastMonth();
  // fallback simples: semana anterior
  return lastWeek();
}
