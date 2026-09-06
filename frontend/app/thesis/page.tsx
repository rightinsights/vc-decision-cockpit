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
    <div className="max-w-[760px] space-y-10">
      <div>
        <h1 className="text-2xl font-medium tracking-tight">Investment thesis</h1>
        <p className="claim-text mt-4 text-[1.25rem] leading-relaxed">{thesis.thesis_text}</p>
      </div>

      <div className="grid gap-8 sm:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-medium">Positive signals</h2>
          <ul className="space-y-1.5 text-sm">{thesis.positive_signals.map((s) => <li key={s} className="border-t border-border pt-1.5">{s}</li>)}</ul>
        </div>
        <div>
          <h2 className="mb-2 text-sm font-medium">Usually outside scope</h2>
          <ul className="space-y-1.5 text-sm text-muted-foreground">{thesis.out_of_scope.map((s) => <li key={s} className="border-t border-border pt-1.5">{s}</li>)}</ul>
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-medium">How the score is built</h2>
        <table className="w-full text-sm">
          <tbody>
            {thesis.criteria.map((c) => (
              <tr key={c.key} className="border-t border-border">
                <td className="py-2 pr-4 align-top">{c.label}</td>
                <td className="py-2 pr-4 align-top text-muted-foreground">{c.description}</td>
                <td className="py-2 text-right align-top tabular-nums">{c.weight}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-muted-foreground">
          Each criterion is scored 1 to 5 by the model with a reason and page references. The application computes the total:
          (score − 1) / 4 × weight, summed and rescaled over criteria that had evidence. 0 to 49 reads Pass, 50 to 69 Watch, 70 to 100 Diligence.
          The recommendation never changes the human decision.
        </p>
      </div>
    </div>
  );
}
