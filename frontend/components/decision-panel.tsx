"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Decision, Verdict } from "@/lib/types";
import { VERDICT_COLOR, VERDICT_LABEL, formatDate } from "@/lib/format";
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
    <div className="grid gap-8 lg:grid-cols-[1fr_320px]">
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
                className="rounded-md border px-4 py-1.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:opacity-50"
                style={{
                  borderColor: VERDICT_COLOR[option],
                  background: active ? VERDICT_COLOR[option] : "transparent",
                  color: active ? "#fff" : VERDICT_COLOR[option],
                }}
              >
                {VERDICT_LABEL[option]}
                {recommendation === option && <span className="ml-1.5 text-xs font-normal opacity-80">(AI)</span>}
              </button>
            );
          })}
        </div>
        <Textarea
          className="mt-3 min-h-[88px] bg-card"
          placeholder="Short rationale. Required."
          value={rationale}
          onChange={(e) => setRationale(e.target.value)}
          disabled={disabled}
        />
        <div className="mt-3 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {disabled ? "Run the analysis before recording a decision." : "Your decision is recorded as a new entry. Earlier decisions stay visible."}
          </p>
          <Button onClick={record} disabled={disabled || busy || !choice || rationale.trim().length < 3}>
            {busy ? "Recording" : "Record decision"}
          </Button>
        </div>
      </div>

      <div className="border-l border-border pl-6">
        <div className="rail-label">Current human decision</div>
        <div className="mt-1"><VerdictMark value={current?.decision ?? null} size="lg" /></div>
        {current ? (
          <>
            <p className="mt-1 text-sm">{current.rationale}</p>
            <p className="mt-1 text-xs text-muted-foreground">{formatDate(current.created_at)}</p>
          </>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">No decision recorded.</p>
        )}
        {history.length > 1 && (
          <ul className="mt-4 space-y-1.5 border-t border-border pt-3 text-xs text-muted-foreground">
            {history.slice(1, 4).map((d) => (
              <li key={d.id}>
                <span className="font-medium text-foreground">{VERDICT_LABEL[d.decision]}</span>, {formatDate(d.created_at, false)}. {d.rationale}
              </li>
            ))}
          </ul>
        )}
        <Link href={`/companies/${companyId}/changes`} className="mt-4 inline-block text-xs font-medium underline underline-offset-2">
          Open what changed
        </Link>
      </div>
    </div>
  );
}
