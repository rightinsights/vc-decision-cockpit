"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Assessment, Decision, MonitoringEvent, Reassessment } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { ReassessmentView } from "./reassessment-view";

interface Props {
  decision: Decision | null;
  assessment: Assessment | null;
  events: MonitoringEvent[];
  busy: boolean;
  onRun: (question: string | undefined) => Promise<Reassessment | null>;
}

function host(url: string | null): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function AgentCheck({ decision, assessment, events, busy, onRun }: Props) {
  const eligible = decision !== null && (decision.decision === "WATCH" || decision.decision === "DILIGENCE");
  const defaultQuestion = assessment?.main_concern
    ? `Is there new external evidence that resolves this concern: ${assessment.main_concern.replace(/\.$/, "")}?`
    : "";
  const [question, setQuestion] = useState<string>("");
  const [result, setResult] = useState<Reassessment | null>(null);

  async function run() {
    const answer = await onRun(question.trim() || undefined);
    if (answer) setResult(answer);
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <label htmlFor="agent-question" className="rail-label">Investment question the agent should answer</label>
          <Textarea
            id="agent-question"
            className="mt-1 min-h-[64px] bg-card"
            placeholder={defaultQuestion || "Run the analysis first."}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={!eligible || busy}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            {eligible
              ? "Leave blank to use the question above. The agent researches the web and returns one sourced finding. It never changes your decision."
              : "Record WATCH or DILIGENCE to enable the agent. Passed companies are not monitored."}
          </p>
        </div>
        <Button onClick={run} disabled={!eligible || busy}>Run agent check</Button>
      </div>

      {result && <ReassessmentView result={result} />}

      {events.length > 0 && (
        <div>
          <div className="rail-label mb-2">Earlier agent checks</div>
          <ul className="divide-y divide-border border-y border-border text-sm">
            {events.map((e) => (
              <li key={e.id} className="grid gap-1 py-2 sm:grid-cols-[150px_1fr]">
                <span className="text-xs text-muted-foreground">{formatDate(e.created_at)}</span>
                <div>
                  <span className={e.event_found ? "" : "text-muted-foreground"}>
                    {e.event_found ? e.summary : `Nothing material for: ${e.investment_question}`}
                  </span>
                  {e.source_url && (
                    <a href={e.source_url} target="_blank" rel="noreferrer" className="ml-2 text-xs underline underline-offset-2">
                      {host(e.source_url)}
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
