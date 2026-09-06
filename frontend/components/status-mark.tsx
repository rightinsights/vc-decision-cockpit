import type { Relation, Verdict } from "@/lib/types";
import { RELATION_COLOR, RELATION_LABEL, VERDICT_COLOR, VERDICT_LABEL } from "@/lib/format";

export function VerdictMark({ value, size = "sm", muted = false }: { value: Verdict | null; size?: "sm" | "lg"; muted?: boolean }) {
  if (!value) {
    return <span className="text-muted-foreground">{muted ? "None" : "Not yet"}</span>;
  }
  const square = size === "lg" ? "size-3.5" : "size-2.5";
  const text = size === "lg" ? "text-xl font-medium" : "text-sm font-medium";
  return (
    <span className={`inline-flex items-center gap-2 ${text}`}>
      <span className={`${square} shrink-0 rounded-[2px]`} style={{ background: VERDICT_COLOR[value] }} aria-hidden />
      {VERDICT_LABEL[value]}
    </span>
  );
}

export function RelationMark({ value }: { value: Relation }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: RELATION_COLOR[value] }}>
      <span className="size-2 rounded-full" style={{ background: RELATION_COLOR[value] }} aria-hidden />
      {RELATION_LABEL[value]}
    </span>
  );
}

export function Score({ value, small = false }: { value: number | null; small?: boolean }) {
  if (value === null || value === undefined) return <span className="text-muted-foreground">–</span>;
  return (
    <span className={small ? "tabular-nums" : "text-2xl font-medium tabular-nums"}>
      {value}
      <span className="text-muted-foreground text-xs font-normal"> / 100</span>
    </span>
  );
}
