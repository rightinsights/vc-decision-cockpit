"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ErrorNotice } from "@/components/notice";
import { ScoreTile, VerdictMark } from "@/components/status-mark";
import { Timeline } from "@/components/timeline";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import type { Analysis, ChangeEntry } from "@/lib/types";

export default function ChangesPage() {
  const { id } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [entries, setEntries] = useState<ChangeEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([api.getAnalysis(id), api.getChanges(id)])
      .then(([a, c]) => {
        if (!active) return;
        setAnalysis(a);
        setEntries(c);
      })
      .catch((err) => {
        if (active) setError(err instanceof ApiError ? err.message : "Could not load the history.");
      });
    return () => {
      active = false;
    };
  }, [id]);

  if (error) return <ErrorNotice message={error} />;
  if (!analysis || !entries) return <p className="text-sm text-muted-foreground">Building decision history</p>;

  const reassessments = entries.filter((e) => e.kind === "ASSESSMENT" && e.recommendation_before !== null).length;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <p className="text-xs text-muted-foreground">
            <Link href="/" className="hover:text-foreground">Pipeline</Link> <span className="mx-1">/</span>
            <Link href={`/companies/${id}`} className="hover:text-foreground">{analysis.company.name}</Link> <span className="mx-1">/</span> What changed
          </p>
          <p className="eyebrow mt-3 mb-1">Decision history</p>
          <h1 className="display text-[56px]">What changed?</h1>
          <p className="mt-2 text-[17px] text-muted-foreground">
            New evidence can change the AI view. Your decision stays yours. {entries.length} entries, {reassessments} {reassessments === 1 ? "reassessment" : "reassessments"}, oldest first.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="rail-label mb-1">AI view now</div>
            <VerdictMark value={analysis.assessment?.recommendation ?? null} size="lg" muted />
          </div>
          <div className="text-right">
            <div className="rail-label mb-1">Your decision</div>
            <VerdictMark value={analysis.decision?.decision ?? null} size="lg" muted />
          </div>
          <ScoreTile value={analysis.assessment?.overall_score ?? null} />
          <Link href={`/companies/${id}`}><Button variant="outline" className="h-10 font-bold">← Decision room</Button></Link>
        </div>
      </div>

      <section className="panel">
        <div className="mb-6 flex items-center justify-between rounded-md bg-muted px-5 py-3">
          <div className="flex items-center gap-3">
            <span className="rail-label">Current human decision</span>
            <VerdictMark value={analysis.decision?.decision ?? null} muted />
          </div>
          <p className="text-sm text-muted-foreground">{analysis.decision?.rationale ?? "No human decision has been recorded."}</p>
        </div>
        <Timeline entries={entries} />
      </section>
    </div>
  );
}
