import type { Criterion, Question } from "@/lib/types";
import { Button } from "@/components/ui/button";

interface Props {
  questions: Question[];
  criteria: Criterion[];
  canGenerate: boolean;
  onGenerate: () => void;
}

export function QuestionList({ questions, criteria, canGenerate, onGenerate }: Props) {
  const labelFor = (basis: string) => criteria.find((c) => c.key === basis)?.label ?? basis;

  if (questions.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border px-5 py-10 text-center text-muted-foreground">
        {canGenerate ? (
          <>
            <p>Five questions whose answers could change the decision.</p>
            <Button className="mt-4 font-bold" onClick={onGenerate}>Generate five questions</Button>
          </>
        ) : (
          <p>Questions are generated from the analyzed claims and gaps.</p>
        )}
      </div>
    );
  }
  return (
    <ol className="space-y-4">
      {questions.map((q) => (
        <li key={q.id} className="panel-soft grid grid-cols-[3.25rem_1fr] gap-x-3 px-5 py-4">
          <span className="display text-[30px] leading-none text-muted-foreground">0{q.position}</span>
          <div>
            <h3 className="text-[17px] font-bold leading-snug">{q.question}</h3>
            <p className="mt-1.5 text-sm"><span className="font-bold">Why it matters:</span> {q.why_it_matters}</p>
            <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
              <div className="rounded-md px-3 py-2" style={{ background: "color-mix(in oklch, var(--diligence) 9%, white)" }}>
                <div className="rail-label" style={{ color: "var(--diligence)" }}>Strong answer</div>
                <p className="mt-1 leading-snug">{q.strong_answer}</p>
              </div>
              <div className="rounded-md px-3 py-2" style={{ background: "color-mix(in oklch, var(--pass) 8%, white)" }}>
                <div className="rail-label" style={{ color: "var(--pass)" }}>Weak answer</div>
                <p className="mt-1 leading-snug">{q.weak_answer}</p>
              </div>
            </div>
            {q.basis && <p className="mt-2 text-xs text-muted-foreground">Targets: {labelFor(q.basis)}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
