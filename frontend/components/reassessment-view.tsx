import type { Assessment, Reassessment } from "@/lib/types";
import { RELATION_LABEL, SOURCE_LABEL, formatDate } from "@/lib/format";
import { RelationMark, Score, VerdictMark } from "./status-mark";

function Column({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0">
      <div className="rail-label mb-2">{label}</div>
      {children}
    </div>
  );
}

function AssessmentSummary({ a }: { a: Assessment | null }) {
  if (!a) return <p className="text-sm text-muted-foreground">No earlier assessment.</p>;
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-3">
        <VerdictMark value={a.recommendation} size="lg" />
        <Score value={a.overall_score} small />
      </div>
      <p className="text-sm leading-snug">{a.main_concern}</p>
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
    <div className="border border-border bg-card">
      <div className="grid gap-6 px-5 py-4 md:grid-cols-3">
        <Column label="Before">
          <AssessmentSummary a={assessment_before} />
        </Column>

        <Column label="New evidence">
          {event && !event.event_found && (
            <p className="text-sm text-muted-foreground">The agent found nothing material for: “{event.investment_question}”</p>
          )}
          {event && event.event_found && (
            <div className="space-y-1.5 text-sm">
              <div className="text-xs text-muted-foreground">
                {event.event_type.replace(/_/g, " ").toLowerCase()}{event.event_date ? `, ${event.event_date}` : ""}, via {SOURCE_LABEL.AGENT.toLowerCase()} ({event.agent_provider})
              </div>
              <p className="leading-snug">{event.summary}</p>
              {event.source_url && (
                <a href={event.source_url} target="_blank" rel="noreferrer" className="inline-block text-xs underline underline-offset-2">
                  Source: {host(event.source_url)}
                </a>
              )}
              {event.claim_or_gap_affected && (
                <p className="text-xs text-muted-foreground">Bears on: {event.claim_or_gap_affected}</p>
              )}
            </div>
          )}
          {result.note_summary && <p className="text-sm leading-snug">{result.note_summary}</p>}
          {result.trigger !== "AGENT" && result.new_evidence.length > 0 && (
            <ul className="mt-2 space-y-1.5 border-t border-border pt-2">
              {result.new_evidence.map((e) => (
                <li key={e.id} className="text-sm leading-snug">
                  <RelationMark value={e.relation} /> <span className="sr-only">{RELATION_LABEL[e.relation]}</span>
                  <span className="ml-1">{e.evidence_text}</span>
                </li>
              ))}
            </ul>
          )}
        </Column>

        <Column label="After">
          <AssessmentSummary a={assessment_after} />
          {deltas.length > 0 ? (
            <ul className="mt-2 space-y-1 border-t border-border pt-2 text-sm">
              {deltas.map((d) => (
                <li key={d.key}>
                  <span className="font-medium">{d.label}</span>{" "}
                  <span className="tabular-nums">{d.old ?? "–"} → {d.new ?? "–"}</span>
                  {d.reason && <div className="text-xs text-muted-foreground">{d.reason}</div>}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 border-t border-border pt-2 text-sm text-muted-foreground">No criterion score moved.</p>
          )}
        </Column>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-paper px-5 py-3 text-sm">
        <div className="flex items-center gap-4">
          <span className="inline-flex items-center gap-2">
            <span className="rail-label">Recommendation</span>
            <VerdictMark value={recommendation.before} />
            <span className="text-muted-foreground">→</span>
            <VerdictMark value={recommendation.after} />
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="rail-label">Human decision</span>
            <VerdictMark value={human_decision?.decision ?? null} muted />
            <span className="text-xs text-muted-foreground">unchanged until you change it</span>
          </span>
        </div>
        <span
          className="rounded-sm px-2 py-0.5 text-xs font-medium"
          style={{
            background: result.matters ? "color-mix(in oklch, var(--diligence) 14%, transparent)" : "var(--muted)",
            color: result.matters ? "var(--diligence)" : "var(--muted-foreground)",
          }}
        >
          {result.matters ? "Matters to the investment case" : "No material change"}
        </span>
      </div>
      <p className="border-t border-border px-5 py-3 text-sm leading-snug text-muted-foreground">{result.explanation}</p>
    </div>
  );
}
