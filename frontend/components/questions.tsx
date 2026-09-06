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
      <div className="border border-dashed border-border px-5 py-8 text-center text-sm text-muted-foreground">
        {canGenerate ? (
          <>
            <p>Five questions whose answers could change the decision.</p>
            <Button className="mt-4" variant="outline" onClick={onGenerate}>Generate five questions</Button>
          </>
        ) : (
          <p>Questions are generated from the analyzed claims and gaps.</p>
        )}
      </div>
    );
  }
  return (
    <ol className="space-y-5">
      {questions.map((q) => (
        <li key={q.id} className="grid grid-cols-[2rem_1fr] gap-x-2">
          <span className="pt-0.5 text-sm tabular-nums text-muted-foreground">{q.position}.</span>
          <div>
            <p className="text-[15px] font-medium leading-snug">{q.question}</p>
            <p className="mt-1 text-sm text-muted-foreground">{q.why_it_matters}</p>
            <div className="mt-2.5 grid gap-3 text-sm sm:grid-cols-2">
              <div className="border-l-2 pl-3" style={{ borderColor: "var(--diligence)" }}>
                <div className="rail-label">Strong answer</div>
                <p className="mt-0.5 leading-snug">{q.strong_answer}</p>
              </div>
              <div className="border-l-2 pl-3" style={{ borderColor: "var(--pass)" }}>
                <div className="rail-label">Weak answer</div>
                <p className="mt-0.5 leading-snug">{q.weak_answer}</p>
              </div>
            </div>
            {q.basis && <p className="mt-2 text-xs text-muted-foreground">Targets: {labelFor(q.basis)}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
