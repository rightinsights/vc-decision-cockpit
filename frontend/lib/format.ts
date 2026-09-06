import type { Relation, Verdict } from "./types";

export function formatDate(iso: string | null | undefined, withTime = true): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const day = date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  if (!withTime) return day;
  const time = date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${day}, ${time}`;
}

export const VERDICT_COLOR: Record<Verdict, string> = {
  PASS: "var(--pass)",
  WATCH: "var(--watch)",
  DILIGENCE: "var(--diligence)",
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  PASS: "Pass",
  WATCH: "Watch",
  DILIGENCE: "Diligence",
};

export const RELATION_COLOR: Record<Relation, string> = {
  SUPPORTS: "var(--diligence)",
  CONTRADICTS: "var(--pass)",
  QUALIFIES: "var(--qualifies)",
};

export const RELATION_LABEL: Record<Relation, string> = {
  SUPPORTS: "Supports",
  CONTRADICTS: "Contradicts",
  QUALIFIES: "Qualifies",
};

export const SOURCE_LABEL: Record<string, string> = {
  DECK: "Deck",
  FOUNDER_NOTE: "Founder note",
  AGENT: "Agent",
};

export function domainOf(url: string | null): string {
  if (!url) return "";
  try {
    return new URL(url.startsWith("http") ? url : `https://${url}`).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function titleCase(value: string): string {
  return value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}
