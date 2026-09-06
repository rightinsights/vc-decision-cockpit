"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Reassessment } from "@/lib/types";
import { ReassessmentView } from "./reassessment-view";

interface Props {
  enabled: boolean;
  busy: boolean;
  onAnalyze: (notes: string) => Promise<Reassessment | null>;
}

export function FounderUpdate({ enabled, busy, onAnalyze }: Props) {
  const [notes, setNotes] = useState("");
  const [result, setResult] = useState<Reassessment | null>(null);

  async function analyze() {
    const answer = await onAnalyze(notes.trim());
    if (answer) {
      setResult(answer);
      setNotes("");
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <Textarea
          className="min-h-[96px] bg-card"
          placeholder="Paste founder meeting notes or an update. Example: Founder says both pilots are paid, $30K and $50K, and both plan to expand if the first deployment works."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={!enabled || busy}
        />
        <div className="mt-2 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {enabled ? "New facts become evidence, the thesis is rescored, and you see only what moved." : "Run the analysis first."}
          </p>
          <Button variant="outline" onClick={analyze} disabled={!enabled || busy || notes.trim().length < 10}>Analyze update</Button>
        </div>
      </div>
      {result && <ReassessmentView result={result} />}
    </div>
  );
}
