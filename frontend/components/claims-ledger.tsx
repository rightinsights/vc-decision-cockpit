import type { Claim, Evidence } from "@/lib/types";
import { SOURCE_LABEL, titleCase } from "@/lib/format";
import { RelationMark } from "./status-mark";

function SourceCell({ ev }: { ev: Evidence }) {
  if (ev.source_url) {
    let host = ev.source_url;
    try {
      host = new URL(ev.source_url).hostname.replace(/^www\./, "");
    } catch {
      /* keep raw */
    }
    return (
      <a href={ev.source_url} target="_blank" rel="noreferrer" className="font-semibold underline underline-offset-2">
        {host} ↗
      </a>
    );
  }
  if (ev.source_page) {
    return <span className="rounded-sm bg-muted px-2 py-0.5 text-xs font-bold">Slide {ev.source_page}</span>;
  }
  return <span>{SOURCE_LABEL[ev.source_type] ?? ev.source_type}</span>;
}

export function ClaimsLedger({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border px-5 py-10 text-center text-muted-foreground">
        Claims and evidence appear here after the deck is analyzed.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="table-head text-left">
            <th className="w-[30%] px-4 py-2.5">Claim</th>
            <th className="w-[28%] px-3 py-2.5">Evidence</th>
            <th className="px-3 py-2.5">Source</th>
            <th className="px-3 py-2.5">Relation</th>
            <th className="w-[22%] px-3 py-2.5">Missing proof</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => {
            const rows = claim.evidence.length ? claim.evidence : [null];
            return rows.map((ev, i) => (
              <tr key={ev ? ev.id : claim.id} className={i === 0 ? "border-t border-border" : ""}>
                {i === 0 && (
                  <td rowSpan={rows.length} className="px-4 py-3.5 align-top">
                    <div className="mb-1 text-[0.68rem] font-bold uppercase tracking-wider text-muted-foreground">{titleCase(claim.category)}</div>
                    <div className="claim-text">“{claim.claim_text}”</div>
                    <div className="mt-1.5 text-xs text-muted-foreground">
                      {claim.source_page ? `Slide ${claim.source_page}, ` : ""}deck evidence {claim.evidence_strength.toLowerCase()}
                    </div>
                  </td>
                )}
                {ev ? (
                  <>
                    <td className="px-3 py-3.5 align-top leading-snug">
                      {ev.evidence_text}
                      {ev.source_type !== "DECK" && (
                        <div className="mt-1 text-xs font-semibold text-muted-foreground">via {SOURCE_LABEL[ev.source_type] ?? ev.source_type}</div>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3.5 align-top"><SourceCell ev={ev} /></td>
                    <td className="whitespace-nowrap px-3 py-3.5 align-top"><RelationMark value={ev.relation} /></td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-3.5 align-top text-muted-foreground">No evidence in the deck</td>
                    <td className="px-3 py-3.5 align-top text-muted-foreground">–</td>
                    <td className="px-3 py-3.5 align-top text-muted-foreground">–</td>
                  </>
                )}
                {i === 0 && (
                  <td rowSpan={rows.length} className="px-3 py-3.5 align-top">
                    {claim.missing_proof ? (
                      <div className="ledger-gap rounded-md px-3 py-2 text-sm font-semibold leading-snug">{claim.missing_proof}</div>
                    ) : (
                      <span className="text-sm text-muted-foreground">No gap identified</span>
                    )}
                  </td>
                )}
              </tr>
            ));
          })}
        </tbody>
      </table>
    </div>
  );
}
