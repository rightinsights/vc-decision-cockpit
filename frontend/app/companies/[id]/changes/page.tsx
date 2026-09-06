"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ErrorNotice } from "@/components/notice";
import { VerdictMark } from "@/components/status-mark";
import { Timeline } from "@/components/timeline";
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
  if (!analysis || !entries) return <p className="text-sm text-muted-foreground">Loading</p>;

  const reassessments = entries.filter((e) => e.kind === "ASSESSMENT" && e.recommendation_before !== null).length;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <Link href={`/companies/${id}`} className="text-xs text-muted-foreground hover:text-foreground">{analysis.company.name}</Link>
          <h1 className="mt-1 text-3xl font-medium tracking-tight">What changed</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {entries.length} entries, {reassessments} {reassessments === 1 ? "reassessment" : "reassessments"}. Oldest first.
          </p>
        </div>
        <div className="flex gap-10 text-right">
          <div>
            <div className="rail-label">AI recommendation now</div>
            <div className="mt-1"><VerdictMark value={analysis.assessment?.recommendation ?? null} size="lg" /></div>
          </div>
          <div>
            <div className="rail-label">Human decision now</div>
            <div className="mt-1"><VerdictMark value={analysis.decision?.decision ?? null} size="lg" muted /></div>
          </div>
        </div>
      </div>
      <Timeline entries={entries} />
    </div>
  );
}
