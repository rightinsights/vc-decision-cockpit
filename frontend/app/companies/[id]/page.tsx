"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { AgentCheck } from "@/components/agent-check";
import { ClaimsLedger } from "@/components/claims-ledger";
import { DeckPanel } from "@/components/deck-panel";
import { DecisionPanel } from "@/components/decision-panel";
import { FounderUpdate } from "@/components/founder-update";
import { ErrorNotice, SectionTitle } from "@/components/notice";
import { QuestionList } from "@/components/questions";
import { ResearchPanel } from "@/components/research-panel";
import { SnapshotRail } from "@/components/snapshot";
import { ScoreTile, VerdictMark } from "@/components/status-mark";
import { Steps } from "@/components/steps";
import { ThesisFit } from "@/components/thesis-fit";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { domainOf } from "@/lib/format";
import type { Analysis, Decision, Reassessment, Research, Verdict } from "@/lib/types";

const STEP_ANALYZE = "Reading the deck, extracting claims, and scoring against the thesis. Usually 30 to 90 seconds.";
const STEP_QUESTIONS = "Writing the five questions that could change the decision.";
const STEP_UPLOAD = "Uploading and reading pages.";
const STEP_AGENT = "The agent is researching the company. This can take a few minutes.";
const STEP_NOTES = "Extracting evidence from the update and rescoring.";
const STEP_RESEARCH = "Searching the web with Brave and reading the results.";

export default function DecisionRoomPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const autoResearch = searchParams.get("research") === "1";
  const autoStarted = useRef(false);
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

  async function run<T>(step: string, action: () => Promise<T>): Promise<T | null> {
    setBusy(step);
    setError(null);
    try {
      const value = await action();
      const [a, h] = await fetchAll();
      setAnalysis(a);
      setHistory(h);
      return value;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The connection dropped before the reply arrived. The work may still have completed; the page has been refreshed.");
      try {
        const [a, h] = await fetchAll();  // the server may have finished even if the reply was lost
        setAnalysis(a);
        setHistory(h);
      } catch {
        /* keep the original error */
      }
      return null;
    } finally {
      setBusy(null);
    }
  }

  const runAgent = (question: string | undefined): Promise<Reassessment | null> => run(STEP_AGENT, () => api.agentCheck(id, question));
  const runResearch = (brief: string | undefined): Promise<Research | null> => run(STEP_RESEARCH, () => api.research(id, brief));
  const analyzeNotes = (notes: string): Promise<Reassessment | null> =>
    run(STEP_NOTES, async () => {
      const note = await api.founderNote(id, notes);
      return api.reassess(id, note.id);
    });
  const analyzeThenQuestions = () =>
    run(STEP_ANALYZE, async () => {
      await api.analyze(id);
      setBusy(STEP_QUESTIONS);
      await api.meetingQuestions(id);
    });

  // A newly created company researches itself once, straight from name and website.
  useEffect(() => {
    if (!autoResearch || !analysis || analysis.research !== null || autoStarted.current) return;
    autoStarted.current = true;
    const timer = setTimeout(() => {
      void runResearch(undefined);
    }, 0);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoResearch, analysis]);

  if (!analysis) {
    return (
      <div className="space-y-4">
        <ErrorNotice message={error} />
        {!error && <p className="text-sm text-muted-foreground">Opening decision room</p>}
      </div>
    );
  }

  const { company, assessment, claims, questions, decision, snapshot, document, thesis, monitoring_events, research } = analysis;
  const canRunAgent = decision !== null && (decision.decision === "WATCH" || decision.decision === "DILIGENCE");

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link href="/" className="hover:text-foreground">Pipeline</Link> <span className="mx-1">/</span> {company.name}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-4">
            <h1 className="display text-[56px]">{company.name}</h1>
            <VerdictMark value={decision?.decision ?? null} size="lg" muted />
          </div>
          <p className="mt-1 text-[17px] text-muted-foreground">
            {company.stage ?? "Stage unknown"} <span className="mx-1">·</span> {company.geography ?? "Geography unknown"}
            {company.website && (
              <>
                <span className="mx-1">·</span>
                <a href={company.website.startsWith("http") ? company.website : `https://${company.website}`} target="_blank" rel="noreferrer" className="underline underline-offset-4">
                  {domainOf(company.website)} ↗
                </a>
              </>
            )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="rail-label mb-1">AI view</div>
            <VerdictMark value={assessment?.recommendation ?? null} size="lg" muted />
          </div>
          <ScoreTile value={assessment?.overall_score ?? null} />
          <Link href={`/companies/${id}/changes`}><Button variant="outline" className="h-10 font-bold">Decision history</Button></Link>
        </div>
      </div>

      <ErrorNotice message={error} onDismiss={() => setError(null)} />

      <Steps analysis={analysis} busy={busy} />

      <DeckPanel
        document={document}
        hasAnalysis={assessment !== null}
        busy={busy}
        questionsMissing={questions.length === 0}
        onUpload={(file) => run(STEP_UPLOAD, () => api.uploadDeck(id, file))}
        onAnalyze={analyzeThenQuestions}
        onQuestions={() => run(STEP_QUESTIONS, () => api.meetingQuestions(id))}
      />

      <div className="grid gap-8 lg:grid-cols-[340px_1fr]">
        <aside className="space-y-8">
          <section className="panel">
            <SectionTitle eyebrow="Company snapshot">{snapshot?.source === "web" ? "What public sources say" : "What the deck says"}</SectionTitle>
            <SnapshotRail snapshot={snapshot} />
          </section>
          <section className="panel">
            <SectionTitle eyebrow="Thesis fit">Criterion scores</SectionTitle>
            <ThesisFit assessment={assessment} criteria={thesis.criteria} />
          </section>
        </aside>

        <div className="min-w-0 space-y-8">
          <section className="panel">
            <SectionTitle eyebrow="Claim → evidence → gap" aside={claims.length ? `${claims.length} claims from the deck` : undefined}>Claims and evidence</SectionTitle>
            <ClaimsLedger claims={claims} />
          </section>

          <section className="panel">
            <SectionTitle eyebrow="Exactly five" aside={questions.length ? "Answers that could change the decision" : undefined}>Questions that could change the decision</SectionTitle>
            <QuestionList
              questions={questions}
              criteria={thesis.criteria}
              canGenerate={assessment !== null && !busy}
              onGenerate={() => run(STEP_QUESTIONS, () => api.meetingQuestions(id))}
            />
          </section>

          <section className="panel">
            <SectionTitle eyebrow="Human decision">AI recommends. You decide.</SectionTitle>
            <DecisionPanel
              companyId={id}
              current={decision}
              history={history}
              recommendation={assessment?.recommendation ?? null}
              disabled={assessment === null || busy !== null}
              onRecord={async (verdict: Verdict, rationale: string) => {
                await run("Recording decision.", () => api.createDecision(id, { decision: verdict, rationale }));
              }}
            />
          </section>

          <section className="panel">
            <SectionTitle eyebrow="Public research" aside="Brave search plus one model call. Facts cite returned URLs only.">Sourced public profile</SectionTitle>
            <ResearchPanel research={research} busy={busy !== null} onRun={runResearch} />
          </section>

          <section className="panel" style={{ borderTopColor: canRunAgent ? "var(--orange)" : undefined }}>
            <SectionTitle eyebrow="OpenClaw agent" aside="One real external research run, returned as evidence">Run agent check</SectionTitle>
            <AgentCheck decision={decision} assessment={assessment} events={monitoring_events} busy={busy !== null} onRun={runAgent} />
          </section>

          <section className="panel">
            <SectionTitle eyebrow="Optional" aside="Paste notes, see only what moved">Founder update</SectionTitle>
            <FounderUpdate enabled={assessment !== null} busy={busy !== null} onAnalyze={analyzeNotes} />
          </section>
        </div>
      </div>
    </div>
  );
}
