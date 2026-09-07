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
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md bg-forest px-4 py-2.5 text-paper">
        <span className="text-[12px] font-bold uppercase tracking-[0.14em]">Brave search → OpenAI → cockpit</span>
        <span className="text-xs opacity-80">No agent loop. Every fact cites a returned URL or is dropped.</span>
      </div>
      <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <label htmlFor="research-brief" className="rail-label">What should the search cover?</label>
          <Textarea
            id="research-brief"
            className="mt-1 min-h-[72px] bg-card text-[15px]"
            placeholder={DEFAULT_BRIEF}
            value={brief}
            onChange={(e) => setBrief(e.target.value)}
            disabled={busy}
          />
        </div>
        <Button className="h-10 px-5 font-bold" onClick={run} disabled={busy}>{shown ? "Run fresh research" : "Research company"}</Button>
      </div>

      {shown && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-xs text-muted-foreground">
            <span>
              {shown.result_count} results across {shown.domain_count} domains, {shown.facts_kept} facts kept
              {shown.facts_dropped > 0 ? `, ${shown.facts_dropped} dropped for citing a URL the search did not return` : ""}.
            </span>
            <span>{formatDate(shown.created_at)}</span>
          </div>
          <div className="grid gap-4 sm:grid-cols-[140px_1fr]">
            <span className="eyebrow">Summary</span>
            <p className="text-[16px] leading-relaxed">{shown.summary}</p>
          </div>
          {shown.entity_note && <p className="text-xs text-muted-foreground">{shown.entity_note}</p>}
          {shown.facts.length > 0 && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {shown.facts.map((fact, i) => (
                <article key={`${fact.source_url}-${i}`} className="rounded-md border border-border bg-muted/40 px-4 py-3" style={{ borderTop: "3px solid var(--forest)" }}>
                  <div className="flex items-baseline justify-between gap-2">
                    <span className="text-[0.68rem] font-bold uppercase tracking-wider text-muted-foreground">{titleCase(fact.category.toLowerCase())}</span>
                    <span className="text-[0.68rem] font-bold uppercase tracking-wider" style={{ color: CONFIDENCE_STYLE[fact.confidence] }}>{fact.confidence} confidence</span>
                  </div>
                  <p className="mt-2 text-sm leading-snug">{fact.finding}</p>
                  <div className="mt-2 text-xs">
                    <a href={fact.source_url} target="_blank" rel="noreferrer" className="font-bold underline underline-offset-2">{fact.source_title || host(fact.source_url)} ↗</a>
                    {fact.publication_date && <span className="ml-2 text-muted-foreground">{fact.publication_date}</span>}
                    {fact.claim_id && fact.relation && <span className="ml-2 text-muted-foreground">{fact.relation.toLowerCase()} a deck claim</span>}
                  </div>
                </article>
              ))}
            </div>
          )}
          {shown.unknowns.length > 0 && (
            <div className="rounded-md px-4 py-3" style={{ background: "color-mix(in oklch, var(--watch) 12%, white)", border: "1px solid color-mix(in oklch, var(--watch) 40%, transparent)" }}>
              <div className="rail-label" style={{ color: "var(--watch)" }}>Still unknown</div>
              <ul className="mt-1 list-disc pl-4 text-sm">
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
