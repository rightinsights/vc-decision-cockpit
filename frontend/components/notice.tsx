export function ErrorNotice({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex items-start justify-between gap-4 rounded-md border px-4 py-3 text-sm"
      style={{ borderColor: "var(--pass)", background: "color-mix(in oklch, var(--pass) 8%, white)" }}
    >
      <p>{message}</p>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="text-xs font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground">
          Dismiss
        </button>
      )}
    </div>
  );
}

export function Progress({ label }: { label: string }) {
  return (
    <div className="space-y-2" aria-live="polite">
      <div className="h-[4px] w-full overflow-hidden rounded-full bg-muted">
        <div className="progress-sweep h-full w-full" />
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function SectionTitle({ eyebrow, children, aside }: { eyebrow?: string; children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        {eyebrow && <p className="eyebrow mb-1">{eyebrow}</p>}
        <h2 className="display text-[26px]">{children}</h2>
      </div>
      {aside && <div className="text-sm text-muted-foreground">{aside}</div>}
    </div>
  );
}
