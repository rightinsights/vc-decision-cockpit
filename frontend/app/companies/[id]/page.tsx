"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ClaimsLedger } from "@/components/claims-ledger";
import { DeckPanel } from "@/components/deck-panel";
import { DecisionPanel } from "@/components/decision-panel";
import { ErrorNotice, SectionTitle } from "@/components/notice";
import { QuestionList } from "@/components/questions";
import { SnapshotRail } from "@/components/snapshot";
import { Score, VerdictMark } from "@/components/status-mark";
import { ThesisFit } from "@/components/thesis-fit";
import { api, ApiError } from "@/lib/api";
import { domainOf } from "@/lib/format";
import type { Analysis, Decision, Verdict } from "@/lib/types";

const STEP_ANALYZE = "Reading the deck, extracting claims, and scoring against the thesis. Usually 30 to 90 seconds.";
const STEP_QUESTIONS = "Writing the five questions that could change the decision.";
const STEP_UPLOAD = "Uploading and reading pages.";

export default function DecisionRoomPage() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [history, setHistory] = useState<Decision[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const fetchAll = useCallback(() => Promise.all([api.getAnalysis(id), api.listDecisions(id)]), [id]);

  useEffect(() => {
    let active = true;
    fetchAll()
      .then(([a, h]) => {
        if (!active) return;
        setAnalysis(a);
        setHistory(h);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load this company.");
      });
    return () => {
      active = false;
    };
  }, [fetchAll]);

  async function run(step: string, action: () => Promise<unknown>) {
    setBusy(step);
    setError(null);
    try {
      await action();
      const [a, h] = await fetchAll();
      setAnalysis(a);
      setHistory(h);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusy(null);
    }
  }

  const analyzeThenQuestions = () =>
    run(STEP_ANALYZE, async () => {
      await api.analyze(id);
      setBusy(STEP_QUESTIONS);
      await api.meetingQuestions(id);
    });

  if (!analysis) {
    return (
      <div className="space-y-4">
        <ErrorNotice message={error} />
        {!error && <p className="text-sm text-muted-foreground">Loading</p>}
      </div>
    );
  }

  const { company, assessment, claims, questions, decision, snapshot, document, thesis } = analysis;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <Link href="/" className="text-xs text-muted-foreground hover:text-foreground">Pipeline</Link>
          <h1 className="mt-1 text-3xl font-medium tracking-tight">{company.name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {[company.stage, company.geography].filter(Boolean).join(", ") || "Stage and geography not yet known"}
            {company.website && (
              <>
                {"  "}
                <a href={company.website.startsWith("http") ? company.website : `https://${company.website}`} target="_blank" rel="noreferrer" className="underline underline-offset-2">
                  {domainOf(company.website)}
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex gap-10 text-right">
          <div>
            <div className="rail-label">AI recommendation</div>
            <div className="mt-1">
              {assessment ? <VerdictMark value={assessment.recommendation} size="lg" /> : <span className="text-muted-foreground">Not analyzed</span>}
            </div>
            {assessment && <div className="mt-0.5 text-xs text-muted-foreground"><Score value={assessment.overall_score} small /></div>}
          </div>
          <div>
            <div className="rail-label">Human decision</div>
            <div className="mt-1"><VerdictMark value={decision?.decision ?? null} size="lg" muted /></div>
          </div>
        </div>
      </div>

      <ErrorNotice message={error} onDismiss={() => setError(null)} />

      <DeckPanel
        document={document}
        hasAnalysis={assessment !== null}
        busy={busy}
        questionsMissing={questions.length === 0}
        onUpload={(file) => run(STEP_UPLOAD, () => api.uploadDeck(id, file))}
        onAnalyze={analyzeThenQuestions}
        onQuestions={() => run(STEP_QUESTIONS, () => api.meetingQuestions(id))}
      />

      <div className="grid gap-10 lg:grid-cols-[300px_1fr]">
        <aside className="space-y-8 lg:sticky lg:top-6 lg:self-start">
          <section>
            <h2 className="mb-2 text-sm font-medium">Snapshot</h2>
            <SnapshotRail snapshot={snapshot} />
          </section>
          <section>
            <h2 className="mb-2 text-sm font-medium">Thesis fit</h2>
            <ThesisFit assessment={assessment} criteria={thesis.criteria} />
          </section>
        </aside>

        <div className="min-w-0 space-y-10">
          <section>
            <SectionTitle aside={claims.length ? `${claims.length} claims from the deck` : undefined}>Claims and evidence</SectionTitle>
            <ClaimsLedger claims={claims} />
          </section>

          <section>
            <SectionTitle aside={questions.length ? "Answers that could change the decision" : undefined}>Five diligence questions</SectionTitle>
            <QuestionList
              questions={questions}
              canGenerate={assessment !== null && !busy}
              onGenerate={() => run(STEP_QUESTIONS, () => api.meetingQuestions(id))}
            />
          </section>

          <section>
            <SectionTitle>Decision</SectionTitle>
            <DecisionPanel
              companyId={id}
              current={decision}
              history={history}
              recommendation={assessment?.recommendation ?? null}
              disabled={assessment === null || busy !== null}
              onRecord={(verdict: Verdict, rationale: string) => run("Recording decision.", () => api.createDecision(id, { decision: verdict, rationale }))}
            />
          </section>
        </div>
      </div>
    </div>
  );
}
