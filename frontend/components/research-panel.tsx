"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Research } from "@/lib/types";
import { formatDate, titleCase } from "@/lib/format";
import { ReassessmentView } from "./reassessment-view";

const DEFAULT_BRIEF =
  "Build a sourced profile: founders and their domain background, product, target customers, evidence of paying customers or pilots, funding, competitors, and material risks.";

interface Props {
  research: Research | null;
  busy: boolean;
  onRun: (brief: string | undefined) => Promise<Research | null>;
}

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

const CONFIDENCE_STYLE: Record<string, string> = {
  HIGH: "var(--diligence)",
  MEDIUM: "var(--watch)",
  LOW: "var(--muted-foreground)",
};

export function ResearchPanel({ research, busy, onRun }: Props) {
  const [brief, setBrief] = useState("");
  const [latest, setLatest] = useState<Research | null>(null);
  const shown = latest ?? research;

  async function run() {
    const result = await onRun(brief.trim() || undefined);
    if (result) setLatest(result);
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <label htmlFor="research-brief" className="rail-label">What should the search cover?</label>
          <Textarea
            id="research-brief"
            className="mt-1 min-h-[64px] bg-card"
            placeholder={DEFAULT_BRIEF}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            disabled={busy}
          />
          <p className="mt-1 text-xs text-muted-foreground">
            Brave web search, read by the model. Every fact must cite a URL the search returned; anything else is dropped.
            No agent run, no OpenClaw cost.
          </p>
        </div>
        <Button variant="outline" onClick={run} disabled={busy}>{shown ? "Research again" : "Research company"}</Button>
      </div>

      {shown && (
        <div className="border border-border bg-card">
          <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-border px-5 py-3 text-xs text-muted-foreground">
            <span>
              {shown.result_count} results across {shown.domain_count} domains, {shown.facts_kept} facts kept
              {shown.facts_dropped > 0 ? `, ${shown.facts_dropped} dropped for citing a URL the search did not return` : ""}.
            </span>
            <span>{formatDate(shown.created_at)}</span>
          </div>
          <div className="px-5 py-4">
            <p className="text-sm leading-snug">{shown.summary}</p>
            {shown.entity_note && <p className="mt-2 text-xs text-muted-foreground">{shown.entity_note}</p>}
          </div>
          {shown.facts.length > 0 && (
            <ul className="divide-y divide-border border-t border-border">
              {shown.facts.map((fact, i) => (
                <li key={`${fact.source_url}-${i}`} className="grid gap-1 px-5 py-3 sm:grid-cols-[120px_1fr]">
                  <div className="text-xs">
                    <div>{titleCase(fact.category.toLowerCase())}</div>
                    <div style={{ color: CONFIDENCE_STYLE[fact.confidence] }}>{fact.confidence.toLowerCase()} confidence</div>
                  </div>
                  <div className="text-sm leading-snug">
                    {fact.finding}
                    <div className="mt-1 text-xs text-muted-foreground">
                      <a href={fact.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{host(fact.source_url)}</a>
                      {fact.publication_date ? `, ${fact.publication_date}` : ""}
                      {fact.claim_id && fact.relation ? `, ${fact.relation.toLowerCase()} a deck claim` : ""}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {shown.unknowns.length > 0 && (
            <div className="border-t border-border px-5 py-3">
              <div className="rail-label">Still unknown</div>
              <ul className="mt-1 list-disc pl-4 text-sm text-muted-foreground">
                {shown.unknowns.map((u) => <li key={u}>{u}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {shown?.reassessment && <ReassessmentView result={shown.reassessment} />}
    </div>
  );
}
