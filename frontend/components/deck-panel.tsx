"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { DocumentInfo } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Progress } from "./notice";

interface Props {
  document: DocumentInfo | null;
  hasAnalysis: boolean;
  busy: string | null;
  onUpload: (file: File) => Promise<unknown>;
  onAnalyze: () => Promise<unknown>;
  onQuestions: () => Promise<unknown>;
  questionsMissing: boolean;
}

export function DeckPanel({ document, hasAnalysis, busy, onUpload, onAnalyze, onQuestions, questionsMissing }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [selected, setSelected] = useState<File | null>(null);

  if (busy) {
    return (
      <div className="panel-soft px-6 py-5">
        <Progress label={busy} />
      </div>
    );
  }

  return (
    <div className="panel-soft flex flex-wrap items-center justify-between gap-4 px-6 py-4">
      <div className="flex items-center gap-4">
        <span className="flex size-11 items-center justify-center rounded-md text-[11px] font-bold text-white" style={{ background: "var(--pass)" }}>PDF</span>
        <div>
          <div className="text-[15px] font-bold">{document ? document.file_name : "Pitch deck (optional)"}</div>
          <div className="text-sm text-muted-foreground">
            {document
              ? `${document.page_count} pages${document.ocr_pages ? `, ${document.ocr_pages} transcribed from images` : ""}, slide references kept, uploaded ${formatDate(document.created_at)}`
              : "Public research runs without it. Add the deck for claim-level scoring and the five questions. PDF up to 25 MB; image-only pages are transcribed."}
          </div>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={input}
          type="file"
          accept="application/pdf"
          className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-3 file:py-1.5 file:text-sm file:font-semibold hover:file:bg-muted"
          onChange={(e) => setSelected(e.target.files?.[0] ?? null)}
        />
        <Button variant="outline" className="font-bold" disabled={!selected} onClick={() => selected && onUpload(selected)}>
          {document ? "Replace deck" : "Upload deck"}
        </Button>
        {document && hasAnalysis && questionsMissing && (
          <Button variant="outline" className="font-bold" onClick={onQuestions}>Generate five questions</Button>
        )}
        {document && (
          <Button className="font-bold" onClick={onAnalyze}>{hasAnalysis ? "Run fresh analysis" : "Analyze deck"}</Button>
        )}
      </div>
    </div>
  );
}
