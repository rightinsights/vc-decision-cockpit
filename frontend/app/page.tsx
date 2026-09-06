"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { AddCompanyDialog } from "@/components/add-company-dialog";
import { ErrorNotice } from "@/components/notice";
import { Score, VerdictMark } from "@/components/status-mark";
import { api, ApiError } from "@/lib/api";
import { domainOf, formatDate } from "@/lib/format";
import type { PipelineRow } from "@/lib/types";

export default function PipelinePage() {
  const [rows, setRows] = useState<PipelineRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .listCompanies()
      .then((data) => {
        if (active) setRows(data);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof ApiError ? err.message : "Could not load the pipeline.");
        setRows([]);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Pipeline</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {rows ? `${rows.length} ${rows.length === 1 ? "company" : "companies"}` : "Loading"}
          </p>
        </div>
        <Button onClick={() => setAdding(true)}>Add company</Button>
      </div>

      <ErrorNotice message={error} onDismiss={() => setError(null)} />

      {rows && rows.length === 0 && !error && (
        <div className="border border-dashed border-border px-6 py-16 text-center">
          <p className="text-base">No companies yet.</p>
          <p className="mt-1 text-sm text-muted-foreground">Add one, upload its pitch deck, and run the analysis.</p>
          <Button className="mt-5" onClick={() => setAdding(true)}>Add company</Button>
        </div>
      )}

      {rows && rows.length > 0 && (
        <div className="overflow-x-auto border border-border bg-card">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th className="px-4 py-2.5 font-normal">Company</th>
                <th className="px-3 py-2.5 font-normal">Stage</th>
                <th className="px-3 py-2.5 font-normal">Geography</th>
                <th className="px-3 py-2.5 font-normal">AI recommendation</th>
                <th className="px-3 py-2.5 font-normal">Human decision</th>
                <th className="px-3 py-2.5 text-right font-normal">Thesis score</th>
                <th className="px-3 py-2.5 font-normal">Main concern</th>
                <th className="px-3 py-2.5 font-normal">Last changed</th>
                <th className="px-3 py-2.5" />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3 align-top">
                    <Link href={`/companies/${row.id}`} className="font-medium hover:underline">{row.name}</Link>
                    <div className="text-xs text-muted-foreground">
                      {domainOf(row.website) || (row.has_deck ? "Deck uploaded" : "No deck yet")}
                    </div>
                  </td>
                  <td className="px-3 py-3 align-top">{row.stage ?? <span className="text-muted-foreground">–</span>}</td>
                  <td className="px-3 py-3 align-top">{row.geography ?? <span className="text-muted-foreground">–</span>}</td>
                  <td className="px-3 py-3 align-top">
                    {row.has_analysis ? <VerdictMark value={row.recommendation} /> : <span className="text-muted-foreground">Not analyzed</span>}
                  </td>
                  <td className="px-3 py-3 align-top"><VerdictMark value={row.decision} muted /></td>
                  <td className="px-3 py-3 text-right align-top"><Score value={row.overall_score} small /></td>
                  <td className="max-w-[320px] px-3 py-3 align-top text-muted-foreground">
                    <span className="line-clamp-2">{row.main_concern ?? ""}</span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 align-top text-muted-foreground">{formatDate(row.last_changed)}</td>
                  <td className="px-3 py-3 text-right align-top">
                    <Link href={`/companies/${row.id}`} className="text-xs font-medium hover:underline">Open decision room</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <AddCompanyDialog open={adding} onOpenChange={setAdding} />
    </div>
  );
}
