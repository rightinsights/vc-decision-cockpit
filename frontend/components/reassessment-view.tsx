import type { Assessment, Reassessment } from "@/lib/types";
import { SOURCE_LABEL, cleanReason, formatDate } from "@/lib/format";
import { RelationMark, Score, VerdictMark } from "./status-mark";

function Column({ label, accent, children }: { label: string; accent?: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 rounded-md border border-border bg-card px-4 py-4" style={{ borderTop: `3px solid ${accent ?? "var(--border)"}` }}>
      <div className="eyebrow mb-3" style={accent ? { color: accent } : undefined}>{label}</div>
      {children}
    </div>
  );
}

function AssessmentSummary({ a }: { a: Assessment | null }) {
  if (!a) return <p className="text-sm text-muted-foreground">No earlier assessment.</p>;
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <VerdictMark value={a.recommendation} size="lg" />
        <Score value={a.overall_score} />
      </div>
      <div>
        <div className="rail-label">Main concern</div>
        <p className="mt-1 text-[15px] leading-snug">{a.main_concern}</p>
      </div>
      <p className="text-xs text-muted-foreground">{formatDate(a.created_at)}</p>
    </div>
  );
}

function host(url: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function ReassessmentView({ result }: { result: Reassessment }) {
  const { event, assessment_before, assessment_after, deltas, recommendation, human_decision } = result;
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        <Column label="Before">
          <AssessmentSummary a={assessment_before} />
        </Column>

        <Column label="New evidence" accent="var(--orange)">
          {event && !event.event_found && (
            <p className="text-sm text-muted-foreground">The agent found nothing material for: “{event.investment_question}”</p>
          )}
          {event && event.event_found && (
            <div className="space-y-2">
              <span className="badge-verdict" style={{ background: "var(--forest)" }}>{event.event_type.replace(/_/g, " ")}</span>
              <h3 className="text-[17px] font-bold leading-snug">{event.summary}</h3>
              <div>
                <div className="rail-label">Why it matters</div>
                <p className="mt-0.5 text-sm leading-snug">{event.relevance}</p>
              </div>
              {event.claim_or_gap_affected && (
                <div>
                  <div className="rail-label">Gap affected</div>
                  <p className="mt-0.5 text-sm leading-snug">{event.claim_or_gap_affected}</p>
                </div>
              )}
              {event.source_url ? (
                <a href={event.source_url} target="_blank" rel="noreferrer" className="inline-block text-sm font-bold underline underline-offset-4">
                  Open source: {host(event.source_url)} ↗
                </a>
              ) : (
                <span className="text-xs text-muted-foreground">No source URL returned</span>
              )}
              <p className="text-xs text-muted-foreground">
                {event.event_date ? `${event.event_date}, ` : ""}via {SOURCE_LABEL.AGENT.toLowerCase()} ({event.agent_provider})
              </p>
            </div>
          )}
          {result.note_summary && <p className="text-[15px] leading-snug">{result.note_summary}</p>}
          {result.trigger !== "AGENT" && result.new_evidence.length > 0 && (
            <ul className="mt-3 space-y-2 border-t border-border pt-3">
              {result.new_evidence.map((e) => (
                <li key={e.id} className="text-sm leading-snug">
                  <RelationMark value={e.relation} /> <span className="ml-1">{e.evidence_text}</span>
                </li>
              ))}
            </ul>
          )}
        </Column>

        <Column label="After" accent="var(--forest)">
          <AssessmentSummary a={assessment_after} />
          {deltas.length > 0 ? (
            <ul className="mt-3 space-y-1.5 border-t border-border pt-3 text-sm">
              {deltas.map((d) => (
                <li key={d.key}>
                  <span className="font-bold">{d.label}</span>{" "}
                  <span className="display text-lg tabular-nums">{d.old ?? "–"} → {d.new ?? "–"}</span>
                  {d.reason && <div className="text-xs text-muted-foreground">{cleanReason(d.reason)}</div>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 border-t border-border pt-3 text-sm text-muted-foreground">No criterion score moved.</p>
          )}
        </Column>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-muted px-5 py-3 text-sm">
        <div className="flex flex-wrap items-center gap-5">
          <span className="inline-flex items-center gap-2">
            <span className="rail-label">Recommendation</span>
            <VerdictMark value={recommendation.before} />
            <span className="text-muted-foreground">→</span>
            <VerdictMark value={recommendation.after} />
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="rail-label">Human decision remains</span>
            <VerdictMark value={human_decision?.decision ?? null} muted />
            <span className="text-xs text-muted-foreground">until you record a new one</span>
          </span>
        </div>
        <span
          className="badge-verdict"
          style={{ background: result.matters ? "var(--orange)" : "var(--muted-foreground)" }}
        >
          {result.matters ? "Matters to the case" : "No material change"}
        </span>
      </div>
      <p className="text-sm leading-snug text-muted-foreground">{result.explanation}</p>
    </div>
  );
}
