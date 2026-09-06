"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { DocumentInfo } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Progress } from "./notice";

interface Props {
  document: DocumentInfo | null;
  hasAnalysis: boolean;
  busy: string | null; // label of the step in flight, or null
  onUpload: (file: File) => Promise<void>;
  onAnalyze: () => Promise<void>;
  onQuestions: () => Promise<void>;
  questionsMissing: boolean;
}

export function DeckPanel({ document, hasAnalysis, busy, onUpload, onAnalyze, onQuestions, questionsMissing }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [selected, setSelected] = useState<File | null>(null);

  if (busy) {
    return (
      <div className="border border-border bg-card px-5 py-4">
        <Progress label={busy} />
      </div>
    );
  }

  if (!document) {
    return (
      <div className="border border-dashed border-border bg-card px-5 py-6">
        <p className="text-base">Upload the pitch deck to start.</p>
        <p className="mt-1 text-sm text-muted-foreground">
          PDF only, up to 25 MB. Text is read page by page so every claim can cite its slide.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input
            ref={input}
            type="file"
            accept="application/pdf"
            className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-background file:px-2.5 file:py-1 file:text-sm hover:file:bg-muted"
            onChange={(e) => setSelected(e.target.files?.[0] ?? null)}
          />
          <Button disabled={!selected} onClick={() => selected && onUpload(selected)}>Upload deck</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border border-border bg-card px-5 py-3 text-sm">
      <div>
        <span className="font-medium">{document.file_name}</span>
        <span className="text-muted-foreground">
          {"  "}{document.page_count} pages, uploaded {formatDate(document.created_at)}
        </span>
      </div>
      <div className="flex items-center gap-2">
        {hasAnalysis && questionsMissing && (
          <Button variant="outline" onClick={onQuestions}>Generate five questions</Button>
        )}
        <Button variant={hasAnalysis ? "outline" : "default"} onClick={onAnalyze}>
          {hasAnalysis ? "Run analysis again" : "Run analysis"}
        </Button>
      </div>
    </div>
  );
}
