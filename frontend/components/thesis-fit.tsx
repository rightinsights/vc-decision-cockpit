import type { Assessment, Criterion } from "@/lib/types";
import { Score, VerdictMark } from "./status-mark";

function Pips({ score }: { score: number | null }) {
  return (
    <span className="inline-flex gap-[3px]" aria-label={score === null ? "no data" : `${score} of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className="h-2.5 w-3 rounded-[1px]"
          style={{
            background: score !== null && n <= score ? "var(--foreground)" : "transparent",
            border: `1px solid ${score === null ? "var(--border)" : "var(--foreground)"}`,
            opacity: score !== null && n <= score ? 1 : 0.45,
          }}
        />
      ))}
    </span>
  );
}

export function ThesisFit({ assessment, criteria }: { assessment: Assessment | null; criteria: Criterion[] }) {
  if (!assessment) {
    return <p className="text-sm text-muted-foreground">Criterion scores appear after the deck is analyzed.</p>;
  }
  return (
    <div>
      <div className="mb-3 flex items-end justify-between">
        <div>
          <div className="rail-label">AI recommendation</div>
          <div className="mt-0.5"><VerdictMark value={assessment.recommendation} /></div>
        </div>
        <div className="text-right">
          <div className="rail-label">Score</div>
          <Score value={assessment.overall_score} small />
          {assessment.used_weight < 100 && (
            <div className="text-[11px] text-muted-foreground">on {assessment.used_weight} of 100 weight</div>
          )}
        </div>
      </div>
      <ul>
        {criteria.map((c) => {
          const item = assessment.criterion_scores[c.key];
          return (
            <li key={c.key} className="border-t border-border py-2">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm">{c.label}</span>
                <span className="flex items-center gap-2">
                  <Pips score={item?.score ?? null} />
                  <span className="w-4 text-right text-xs tabular-nums text-muted-foreground">{item?.score ?? "–"}</span>
                </span>
              </div>
              {item?.reason && <p className="mt-1 text-xs leading-snug text-muted-foreground">{item.reason}</p>}
            </li>
          );
        })}
      </ul>
      <div className="mt-3 border-t border-border pt-3 text-sm">
        <div className="rail-label">Main concern</div>
        <p className="mt-0.5 leading-snug">{assessment.main_concern}</p>
      </div>
      {assessment.summary && <p className="mt-3 text-xs leading-snug text-muted-foreground">{assessment.summary}</p>}
    </div>
  );
}
