import type { Snapshot } from "@/lib/types";

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="border-t border-border py-3 first:border-t-0 first:pt-0">
      <div className="rail-label">{label}</div>
      <div className="mt-1 text-[15px] leading-snug">{value ?? <span className="text-muted-foreground">Not stated in sources</span>}</div>
    </div>
  );
}

export function SnapshotRail({ snapshot }: { snapshot: Snapshot | null }) {
  if (!snapshot) {
    return <p className="text-sm text-muted-foreground">The snapshot fills in from public research, then from the deck.</p>;
  }
  const founders = snapshot.founders.length
    ? snapshot.founders.map((f) => (
        <div key={f.name} className="mb-2 last:mb-0">
          <span className="font-bold">{f.name}</span>
          {f.role && <span className="text-muted-foreground">, {f.role}</span>}
          {f.domain_background && <div className="text-sm text-muted-foreground">{f.domain_background}</div>}
        </div>
      ))
    : null;
  return (
    <div>
      <Row label="Problem" value={snapshot.problem} />
      <Row label="Workflow" value={snapshot.workflow} />
      <Row label="Customer" value={snapshot.customer} />
      <Row label="Buyer" value={snapshot.buyer} />
      <Row label="Solution" value={snapshot.solution} />
      <Row label="Traction" value={snapshot.traction.length ? <ul className="list-disc pl-4">{snapshot.traction.map((t) => <li key={t}>{t}</li>)}</ul> : null} />
      <Row label="Business model" value={snapshot.business_model} />
      <Row label="Founders and domain background" value={founders} />
      <Row label="Funding ask" value={snapshot.funding_ask} />
      {snapshot.unknowns.length > 0 && (
        <Row label="Not in the deck" value={<ul className="list-disc pl-4 text-muted-foreground">{snapshot.unknowns.map((u) => <li key={u}>{u}</li>)}</ul>} />
      )}
    </div>
  );
}
