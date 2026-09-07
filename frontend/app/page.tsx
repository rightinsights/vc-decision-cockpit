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

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat-tile flex flex-1 items-center justify-between px-7 py-5">
      <span className="text-sm">{label}</span>
      <span className="display text-3xl tabular-nums">{value}</span>
    </div>
  );
}

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

  const count = (fn: (r: PipelineRow) => boolean) => (rows ? rows.filter(fn).length : "–");

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="eyebrow mb-2">Active dealflow</p>
          <h1 className="display text-[40px]">Investment pipeline</h1>
        </div>
        <Button size="lg" className="px-5 text-[15px] font-bold" onClick={() => setAdding(true)}>+ Add company</Button>
      </div>

      <div className="flex overflow-hidden rounded-md">
        <Stat label="Companies" value={rows ? rows.length : "–"} />
        <Stat label="In diligence" value={count((r) => r.decision === "DILIGENCE")} />
        <Stat label="Watching" value={count((r) => r.decision === "WATCH")} />
        <Stat label="Awaiting decision" value={count((r) => r.decision === null)} />
      </div>

      <ErrorNotice message={error} onDismiss={() => setError(null)} />

      <div className="panel-soft overflow-hidden">
        <div className="flex items-end justify-between px-7 pb-4 pt-6">
          <div>
            <p className="eyebrow mb-1">Pipeline</p>
            <h2 className="display text-[28px]">Companies under review</h2>
          </div>
          <span className="text-sm text-muted-foreground">{rows ? `${rows.length} total` : ""}</span>
        </div>

        {rows && rows.length === 0 && !error && (
          <div className="border-t border-border px-7 py-16 text-center">
            <p className="display text-2xl">No companies yet.</p>
            <p className="mt-2 text-muted-foreground">Add one, upload its pitch deck, and run the analysis.</p>
            <Button className="mt-6 font-bold" onClick={() => setAdding(true)}>+ Add company</Button>
          </div>
        )}

        {rows && rows.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="table-head text-left">
                  <th className="px-7 py-3">Company</th>
                  <th className="px-3 py-3">Stage / geography</th>
                  <th className="px-3 py-3">AI view</th>
                  <th className="px-3 py-3">Your decision</th>
                  <th className="px-3 py-3 text-right">Score</th>
                  <th className="px-3 py-3">Main concern</th>
                  <th className="px-3 py-3">Changed</th>
                  <th className="px-7 py-3" />
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-t border-border hover:bg-muted/40">
                    <td className="px-7 py-4 align-top">
                      <Link href={`/companies/${row.id}`} className="text-[15px] font-bold hover:underline">{row.name}</Link>
                      <div className="text-xs text-muted-foreground">{domainOf(row.website) || (row.has_deck ? "Deck uploaded" : "No deck yet")}</div>
                    </td>
                    <td className="px-3 py-4 align-top">
                      <div>{row.stage ?? <span className="text-muted-foreground">Stage unknown</span>}</div>
                      <div className="text-xs text-muted-foreground">{row.geography ?? ""}</div>
                    </td>
                    <td className="px-3 py-4 align-top">
                      {row.has_analysis ? <VerdictMark value={row.recommendation} /> : <VerdictMark value={null} muted />}
                    </td>
                    <td className="px-3 py-4 align-top"><VerdictMark value={row.decision} muted /></td>
                    <td className="px-3 py-4 text-right align-top"><Score value={row.overall_score} small /></td>
                    <td className="max-w-[340px] px-3 py-4 align-top text-muted-foreground">
                      <span className="line-clamp-2">{row.main_concern ?? (row.has_deck ? "Run the analysis." : "Upload a deck or run research.")}</span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 align-top text-muted-foreground">{formatDate(row.last_changed, false)}</td>
                    <td className="px-7 py-4 text-right align-top">
                      <Link href={`/companies/${row.id}`} className="whitespace-nowrap text-sm font-bold hover:underline">Open room →</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <AddCompanyDialog open={adding} onOpenChange={setAdding} />
    </div>
  );
}
