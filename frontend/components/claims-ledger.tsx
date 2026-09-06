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
      <a href={ev.source_url} target="_blank" rel="noreferrer" className="underline decoration-border underline-offset-2 hover:decoration-foreground">
        {host}
      </a>
    );
  }
  if (ev.source_page) return <span>Slide {ev.source_page}</span>;
  return <span>{SOURCE_LABEL[ev.source_type] ?? ev.source_type}</span>;
}

export function ClaimsLedger({ claims }: { claims: Claim[] }) {
  if (claims.length === 0) {
    return (
      <p className="border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground">
        Claims and evidence appear here after the deck is analyzed.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto border border-border bg-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th className="w-[30%] px-4 py-2.5 font-normal">Claim</th>
            <th className="w-[30%] px-3 py-2.5 font-normal">Evidence</th>
            <th className="px-3 py-2.5 font-normal">Source</th>
            <th className="px-3 py-2.5 font-normal">Relation</th>
            <th className="w-[22%] px-3 py-2.5 font-normal">Missing proof</th>
          </tr>
        </thead>
        <tbody>
          {claims.map((claim) => {
            const rows = claim.evidence.length ? claim.evidence : [null];
            return rows.map((ev, i) => (
              <tr key={ev ? ev.id : claim.id} className={i === 0 ? "border-t border-border first:border-t-0" : ""}>
                {i === 0 && (
                  <td rowSpan={rows.length} className="px-4 py-3 align-top">
                    <div className="claim-text">“{claim.claim_text}”</div>
                    <div className="mt-1.5 text-xs text-muted-foreground">
                      {titleCase(claim.category)}
                      {claim.source_page ? `, slide ${claim.source_page}` : ""}
                      {", deck evidence "}{claim.evidence_strength.toLowerCase()}
                    </div>
                  </td>
                )}
                {ev ? (
                  <>
                    <td className="px-3 py-3 align-top leading-snug">{ev.evidence_text}</td>
                    <td className="whitespace-nowrap px-3 py-3 align-top text-muted-foreground"><SourceCell ev={ev} /></td>
                    <td className="whitespace-nowrap px-3 py-3 align-top"><RelationMark value={ev.relation} /></td>
                  </>
                ) : (
                  <>
                    <td className="px-3 py-3 align-top text-muted-foreground">No evidence in the deck</td>
                    <td className="px-3 py-3 align-top text-muted-foreground">–</td>
                    <td className="px-3 py-3 align-top text-muted-foreground">–</td>
                  </>
                )}
                {i === 0 && (
                  <td rowSpan={rows.length} className="px-3 py-3 align-top">
                    {claim.missing_proof ? (
                      <div className="ledger-gap px-2.5 py-2 text-xs leading-snug">{claim.missing_proof}</div>
                    ) : (
                      <span className="text-xs text-muted-foreground">Nothing further listed</span>
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
