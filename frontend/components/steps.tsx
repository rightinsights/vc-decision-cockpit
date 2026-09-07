import type { Analysis } from "@/lib/types";

interface Step {
  label: string;
  hint: string;
  done: boolean;
}

export function Steps({ analysis, busy }: { analysis: Analysis; busy: string | null }) {
  const steps: Step[] = [
    { label: "Public research", hint: "Brave + model, automatic", done: analysis.research !== null },
    { label: "Deck", hint: "optional, claim-level", done: analysis.document !== null },
    { label: "Thesis fit", hint: "score and five questions", done: analysis.assessment !== null },
    { label: "Your decision", hint: "pass, watch, diligence", done: analysis.decision !== null },
    { label: "Agent check", hint: "one real OpenClaw run", done: analysis.monitoring_events.length > 0 },
  ];
  const current = steps.findIndex((s) => !s.done);
  return (
    <ol className="flex flex-wrap items-stretch gap-2">
      {steps.map((s, i) => {
        const active = i === current;
        return (
          <li
            key={s.label}
            className="flex min-w-[170px] flex-1 items-center gap-3 rounded-md border px-3 py-2"
            style={{
              borderColor: s.done ? "var(--forest)" : active ? "var(--orange)" : "var(--border)",
              background: s.done ? "color-mix(in oklch, var(--forest) 8%, white)" : "var(--card)",
            }}
          >
            <span
              className="flex size-7 shrink-0 items-center justify-center rounded-full text-[12px] font-bold"
              style={{
                background: s.done ? "var(--forest)" : active ? "var(--orange)" : "var(--muted)",
                color: s.done || active ? "#fff" : "var(--muted-foreground)",
              }}
            >
              {s.done ? "✓" : i + 1}
            </span>
            <span className="min-w-0">
              <span className="block text-[13px] font-bold leading-tight">{s.label}</span>
              <span className="block truncate text-[11px] text-muted-foreground">{active && busy ? "in progress" : s.hint}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
