import type { ChangeEntry } from "@/lib/types";
import { cleanReason, formatDate } from "@/lib/format";
import { Score, VerdictMark } from "./status-mark";

function host(url: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

const KIND_LABEL: Record<ChangeEntry["kind"], string> = {
  DECK_UPLOADED: "Deck",
  ASSESSMENT: "AI",
  DECISION: "Human",
  AGENT_EVENT: "OpenClaw",
  FOUNDER_NOTE: "Founder",
  QUESTIONS: "AI",
  RESEARCH: "Brave",
};

function Marker({ kind }: { kind: ChangeEntry["kind"] }) {
  const color =
    kind === "DECISION" ? "var(--orange)" :
    kind === "AGENT_EVENT" ? "var(--forest)" :
    kind === "FOUNDER_NOTE" ? "var(--watch)" :
    kind === "RESEARCH" ? "var(--diligence)" :
    "var(--muted-foreground)";
  const filled = kind === "DECISION" || kind === "AGENT_EVENT" || kind === "FOUNDER_NOTE" || kind === "RESEARCH";
  return (
    <span
      className="mt-1.5 block size-3 rounded-full"
      style={{ background: filled ? color : "var(--card)", border: `2px solid ${color}` }}
      aria-hidden
    />
  );
}

export function Timeline({ entries }: { entries: ChangeEntry[] }) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">Nothing has happened yet. Upload a deck to start the record.</p>;
  }
  return (
    <ol className="relative border-l-2 border-border pl-7">
      {entries.map((e) => {
        const isReassessment = e.kind === "ASSESSMENT" && e.recommendation_before !== null;
        return (
          <li key={e.id} className="relative pb-8 last:pb-0">
            <span className="absolute -left-[36px] top-0"><Marker kind={e.kind} /></span>
            <div className="text-[0.68rem] font-bold uppercase tracking-wider text-muted-foreground">
              {KIND_LABEL[e.kind]} <span className="mx-1">·</span> {formatDate(e.ts)}
            </div>
            <div className="mt-0.5 flex flex-wrap items-baseline gap-x-3">
              <h3 className="text-[17px] font-bold">{e.title}</h3>
              {e.kind === "DECISION" && <VerdictMark value={e.recommendation} />}
              {e.kind === "ASSESSMENT" && !isReassessment && (
                <span className="inline-flex items-center gap-2 text-sm">
                  <VerdictMark value={e.recommendation} /> <Score value={e.overall_score} small />
                </span>
              )}
            </div>
            <p className="mt-1 max-w-[72ch] text-[15px] leading-snug">{e.detail}</p>
            {e.source_url && (
              <a href={e.source_url} target="_blank" rel="noreferrer" className="mt-1 inline-block text-sm font-bold underline underline-offset-4">
                Open source: {host(e.source_url)} ↗
              </a>
            )}

            {isReassessment && (
              <div className="panel-soft mt-3 grid max-w-[760px] gap-4 px-5 py-4 sm:grid-cols-[1fr_auto_1fr]">
                <div>
                  <div className="eyebrow">Before</div>
                  <div className="mt-1.5"><VerdictMark value={e.recommendation_before} size="lg" /></div>
                </div>
                <div className="hidden items-center text-2xl text-muted-foreground sm:flex">→</div>
                <div>
                  <div className="eyebrow">After</div>
                  <div className="mt-1.5 flex items-center gap-3"><VerdictMark value={e.recommendation} size="lg" /> <Score value={e.overall_score} small /></div>
                </div>
                <div className="sm:col-span-3 border-t border-border pt-3">
                  <div className="rail-label">What changed</div>
                  {e.deltas.length ? (
                    <ul className="mt-1 space-y-1 text-sm">
                      {e.deltas.map((d) => (
                        <li key={d.key}>
                          <span className="font-bold">{d.label}</span> <span className="display text-lg tabular-nums">{d.old ?? "–"} → {d.new ?? "–"}</span>
                          {d.reason && <span className="text-muted-foreground">. {cleanReason(d.reason)}</span>}
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
