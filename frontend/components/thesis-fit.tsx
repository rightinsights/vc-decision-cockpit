import type { Assessment, Criterion } from "@/lib/types";
import { cleanReason } from "@/lib/format";
import { Score, VerdictMark } from "./status-mark";

function Track({ score }: { score: number | null }) {
  const pct = score === null ? 0 : (score / 5) * 100;
  const color = score === null ? "var(--muted)" : score >= 4 ? "var(--diligence)" : score >= 3 ? "var(--watch)" : "var(--pass)";
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-muted" aria-label={score === null ? "no data" : `${score} of 5`}>
      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

export function ThesisFit({ assessment, criteria }: { assessment: Assessment | null; criteria: Criterion[] }) {
  if (!assessment) {
    return <p className="text-sm text-muted-foreground">Criterion scores appear after the deck is analyzed.</p>;
  }
  return (
    <div>
      <div className="mb-4 flex items-end justify-between rounded-md bg-muted px-4 py-3">
        <div>
          <div className="rail-label mb-1">Recommendation</div>
          <VerdictMark value={assessment.recommendation} size="lg" />
        </div>
        <div className="text-right">
          <div className="rail-label">Score</div>
          <Score value={assessment.overall_score} />
          {assessment.used_weight < 100 && (
            <div className="text-[11px] text-muted-foreground">on {assessment.used_weight} of 100 weight</div>
          )}
        </div>
      </div>
      <ul>
        {criteria.map((c) => {
          const item = assessment.criterion_scores[c.key];
          return (
            <li key={c.key} className="border-t border-border py-3">
              <div className="flex items-center justify-between gap-3">
                <span className="text-[15px] font-semibold">{c.label}</span>
                <span className="display text-xl tabular-nums">{item?.score ?? "?"}<span className="text-xs font-normal text-muted-foreground">/5</span></span>
              </div>
              <div className="mt-1.5"><Track score={item?.score ?? null} /></div>
              {item?.reason && <p className="mt-1.5 text-sm leading-snug text-muted-foreground">{cleanReason(item.reason)}</p>}
            </li>
          );
        })}
      </ul>
      <div className="mt-4 rounded-md px-4 py-3" style={{ background: "color-mix(in oklch, var(--orange) 10%, white)", border: "1px solid color-mix(in oklch, var(--orange) 40%, transparent)" }}>
        <div className="rail-label" style={{ color: "var(--orange)" }}>Main concern</div>
        <p className="mt-1 text-[15px] font-semibold leading-snug">{assessment.main_concern}</p>
      </div>
      {assessment.summary && <p className="mt-3 text-sm leading-snug text-muted-foreground">{assessment.summary}</p>}
    </div>
  );
}
