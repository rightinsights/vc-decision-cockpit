import type { Relation, Verdict } from "@/lib/types";
import { RELATION_COLOR, RELATION_LABEL, VERDICT_COLOR } from "@/lib/format";

export function VerdictMark({ value, size = "sm", muted = false }: { value: Verdict | null; size?: "sm" | "lg"; muted?: boolean }) {
  const big = size === "lg" ? "text-[0.85rem] px-3 py-1.5" : "";
  if (!value) {
    return <span className={`badge-verdict badge-empty ${big}`}>{muted ? "Not set" : "Pending"}</span>;
  }
  return (
    <span className={`badge-verdict ${big}`} style={{ background: VERDICT_COLOR[value] }}>
      {value}
    </span>
  );
}

export function RelationMark({ value }: { value: Relation }) {
  return (
    <span
      className="inline-flex items-center rounded-sm px-1.5 py-0.5 text-[0.68rem] font-bold uppercase tracking-wider"
      style={{ color: RELATION_COLOR[value], background: `color-mix(in oklch, ${RELATION_COLOR[value]} 12%, white)` }}
    >
      {RELATION_LABEL[value]}
    </span>
  );
}

export function Score({ value, small = false }: { value: number | null; small?: boolean }) {
  if (value === null || value === undefined) return <span className="text-muted-foreground">–</span>;
  return (
    <span className={small ? "tabular-nums font-semibold" : "display text-4xl tabular-nums"}>
      {value}
      <span className="text-muted-foreground text-xs font-normal"> / 100</span>
    </span>
  );
}

export function ScoreTile({ value, label = "Thesis score" }: { value: number | null; label?: string }) {
  return (
    <div className="stat-tile flex min-w-[130px] flex-col items-end rounded-md px-4 py-3">
      <span className="text-[0.68rem] font-bold uppercase tracking-[0.12em] opacity-80">{label}</span>
      <span className="display text-[34px] leading-none tabular-nums">
        {value ?? "–"}
        <span className="text-sm font-normal opacity-70"> /100</span>
      </span>
    </div>
  );
}
