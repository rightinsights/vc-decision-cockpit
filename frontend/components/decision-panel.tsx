"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Decision, Verdict } from "@/lib/types";
import { VERDICT_COLOR, formatDate } from "@/lib/format";
import { VerdictMark } from "./status-mark";

const OPTIONS: Verdict[] = ["PASS", "WATCH", "DILIGENCE"];

interface Props {
  companyId: string;
  current: Decision | null;
  history: Decision[];
  recommendation: Verdict | null;
  disabled: boolean;
  onRecord: (decision: Verdict, rationale: string) => Promise<void>;
}

export function DecisionPanel({ companyId, current, history, recommendation, disabled, onRecord }: Props) {
  const [choice, setChoice] = useState<Verdict | null>(null);
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);

  async function record() {
    if (!choice || rationale.trim().length < 3) return;
    setBusy(true);
    try {
      await onRecord(choice, rationale.trim());
      setChoice(null);
      setRationale("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[320px_1fr]">
      <div className="rounded-md bg-muted px-5 py-4">
        <div className="rail-label mb-2">Current decision</div>
        <VerdictMark value={current?.decision ?? null} size="lg" muted />
        {current ? (
          <>
            <p className="mt-3 text-[15px] leading-snug">{current.rationale}</p>
            <p className="mt-1 text-xs text-muted-foreground">{formatDate(current.created_at)}</p>
          </>
        ) : (
          <p className="mt-3 text-sm text-muted-foreground">No decision recorded. Earlier decisions stay visible once you add one.</p>
        )}
        {history.length > 1 && (
          <ul className="mt-4 space-y-1.5 border-t border-border pt-3 text-xs text-muted-foreground">
            {history.slice(1, 4).map((d) => (
              <li key={d.id}>
                <span className="font-bold text-foreground">{d.decision}</span>, {formatDate(d.created_at, false)}. {d.rationale}
              </li>
            ))}
          </ul>
        )}
        <Link href={`/companies/${companyId}/changes`} className="mt-4 inline-block text-sm font-bold underline underline-offset-4">
          Open decision history →
        </Link>
      </div>

      <div>
        <div className="flex flex-wrap gap-2">
          {OPTIONS.map((option) => {
            const active = choice === option;
            return (
              <button
                key={option}
                type="button"
                disabled={disabled}
                onClick={() => setChoice(option)}
                aria-pressed={active}
                className="rounded-md border-2 px-5 py-2 text-sm font-bold uppercase tracking-wider transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
                style={{
                  borderColor: VERDICT_COLOR[option],
                  background: active ? VERDICT_COLOR[option] : "transparent",
                  color: active ? "#fff" : VERDICT_COLOR[option],
                }}
              >
                {option}
                {recommendation === option && <span className="ml-1.5 text-[10px] font-semibold opacity-80">AI</span>}
              </button>
            );
          })}
        </div>
        <label htmlFor="rationale" className="rail-label mt-4 block">Decision rationale</label>
        <Textarea
          id="rationale"
          className="mt-1 min-h-[96px] bg-card text-[15px]"
          placeholder="What evidence drove your decision?"
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={disabled}
        />
        <div className="mt-3 flex items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            {disabled ? "Run the analysis before recording a decision." : "Recorded as a new entry. The AI never changes it."}
          </p>
          <Button className="font-bold" onClick={record} disabled={disabled || busy || !choice || rationale.trim().length < 3}>
            {busy ? "Recording" : choice ? `Record ${choice}` : "Record decision"}
          </Button>
        </div>
      </div>
    </div>
  );
}
