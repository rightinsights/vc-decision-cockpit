"use client";

import { useEffect, useState } from "react";
import { ErrorNotice } from "@/components/notice";
import { api, ApiError } from "@/lib/api";
import type { Thesis } from "@/lib/types";

export default function ThesisPage() {
  const [thesis, setThesis] = useState<Thesis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getThesis().then(setThesis).catch((err) => setError(err instanceof ApiError ? err.message : "Could not load the thesis."));
  }, []);

  if (error) return <ErrorNotice message={error} />;
  if (!thesis) return <p className="text-sm text-muted-foreground">Loading</p>;

  return (
    <div className="space-y-8">
      <div>
        <p className="eyebrow mb-2">Decision lens</p>
        <h1 className="display text-[56px]">Investment thesis</h1>
        <p className="display mt-6 max-w-[900px] text-[26px] font-medium leading-snug">{thesis.thesis_text}</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel">
          <p className="eyebrow mb-1">Positive signals</p>
          <h2 className="display mb-4 text-2xl">What we look for</h2>
          <ul className="space-y-2 text-[15px]">{thesis.positive_signals.map((s) => <li key={s} className="border-t border-border pt-2">{s}</li>)}</ul>
        </section>
        <section className="panel" style={{ borderTopColor: "var(--pass)" }}>
          <p className="eyebrow mb-1" style={{ color: "var(--pass)" }}>Usually outside scope</p>
          <h2 className="display mb-4 text-2xl">What we pass on</h2>
          <ul className="space-y-2 text-[15px] text-muted-foreground">{thesis.out_of_scope.map((s) => <li key={s} className="border-t border-border pt-2">{s}</li>)}</ul>
        </section>
      </div>

      {thesis.investor_note && (
        <section className="panel" style={{ borderTopColor: "var(--orange)" }}>
          <p className="eyebrow mb-1">About the investor</p>
          <h2 className="display mb-3 text-2xl">Why this thesis</h2>
          <p className="max-w-[900px] text-[15px] leading-relaxed">{thesis.investor_note}</p>
        </section>
      )}

      <section className="panel">
        <p className="eyebrow mb-1">Scoring</p>
        <h2 className="display mb-4 text-2xl">How the score is built</h2>
        <table className="w-full text-[15px]">
          <thead>
            <tr className="table-head text-left"><th className="px-3 py-2">Criterion</th><th className="px-3 py-2">What it measures</th><th className="px-3 py-2 text-right">Weight</th></tr>
          </thead>
          <tbody>
            {thesis.criteria.map((c) => (
              <tr key={c.key} className="border-t border-border">
                <td className="px-3 py-2.5 align-top font-bold">{c.label}</td>
                <td className="px-3 py-2.5 align-top text-muted-foreground">{c.description}</td>
                <td className="px-3 py-2.5 text-right align-top tabular-nums">{c.weight}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-4 text-sm text-muted-foreground">
          Each criterion is scored 1 to 5 by the model with a reason and slide references. The application computes the total:
          (score − 1) / 4 × weight, summed and rescaled over criteria that had evidence. 0 to 49 reads PASS, 50 to 69 WATCH, 70 to 100 DILIGENCE.
          The recommendation never changes the human decision.
        </p>
      </section>
    </div>
  );
}
