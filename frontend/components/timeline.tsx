import type { ChangeEntry } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Score, VerdictMark } from "./status-mark";

function host(url: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function Marker({ kind }: { kind: ChangeEntry["kind"] }) {
  const color =
    kind === "DECISION" ? "var(--foreground)" :
    kind === "AGENT_EVENT" ? "var(--diligence)" :
    kind === "FOUNDER_NOTE" ? "var(--watch)" :
    "var(--muted-foreground)";
  const filled = kind === "DECISION" || kind === "AGENT_EVENT" || kind === "FOUNDER_NOTE";
  return (
    <span
      className="mt-1.5 block size-2.5 rounded-full"
      style={{ background: filled ? color : "var(--card)", border: `1.5px solid ${color}` }}
      aria-hidden
    />
  );
}

export function Timeline({ entries }: { entries: ChangeEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing has happened yet. Upload a deck to start the record.</p>;
  }
  return (
    <ol className="relative border-l border-border pl-6">
      {entries.map((e) => {
        const isReassessment = e.kind === "ASSESSMENT" && e.recommendation_before !== null;
        return (
          <li key={e.id} className="relative pb-8 last:pb-0">
            <span className="absolute -left-[31px] top-0"><Marker kind={e.kind} /></span>
            <div className="text-xs text-muted-foreground">{formatDate(e.ts)}</div>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-3">
              <h3 className="text-[15px] font-medium">{e.title}</h3>
              {e.kind === "DECISION" && <VerdictMark value={e.recommendation} />}
              {e.kind === "ASSESSMENT" && !isReassessment && (
                <span className="inline-flex items-center gap-2 text-sm">
                  <VerdictMark value={e.recommendation} /> <Score value={e.overall_score} small />
                </span>
              )}
            </div>
            <p className="mt-1 max-w-[70ch] text-sm leading-snug">{e.detail}</p>
            {e.source_url && (
              <a href={e.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-xs underline underline-offset-2">
                Source: {host(e.source_url)}
              </a>
            )}

            {isReassessment && (
              <div className="mt-3 grid max-w-[720px] gap-4 border border-border bg-card px-4 py-3 sm:grid-cols-[1fr_auto_1fr]">
                <div>
                  <div className="rail-label">Before</div>
                  <div className="mt-1"><VerdictMark value={e.recommendation_before} /></div>
                </div>
                <div className="hidden items-center text-muted-foreground sm:flex">→</div>
                <div>
                  <div className="rail-label">After</div>
                  <div className="mt-1 flex items-center gap-2"><VerdictMark value={e.recommendation} /> <Score value={e.overall_score} small /></div>
                </div>
                <div className="sm:col-span-3">
                  <div className="rail-label">What changed</div>
                  {e.deltas.length ? (
                    <ul className="mt-1 space-y-0.5 text-sm">
                      {e.deltas.map((d) => (
                        <li key={d.key}>
                          <span className="font-medium">{d.label}</span> <span className="tabular-nums">{d.old ?? "–"} → {d.new ?? "–"}</span>
                          {d.reason && <span className="text-muted-foreground">. {d.reason}</span>}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-sm text-muted-foreground">No criterion score moved.</p>
                  )}
                  <p className="mt-2 text-xs text-muted-foreground">
                    Human decision at the time: {e.human_decision_at_time ?? "none recorded"}. It stays until changed by hand.
                  </p>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
