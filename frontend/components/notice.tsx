export function ErrorNotice({ message, onDismiss }: { message: string | null; onDismiss?: () => void }) {
  if (!message) return null;
  return (
    <div role="alert" className="flex items-start justify-between gap-4 border-l-2 pl-3 text-sm" style={{ borderColor: "var(--pass)" }}>
      <p>{message}</p>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="text-muted-foreground hover:text-foreground text-xs">
          Dismiss
        </button>
      )}
    </div>
  );
}

export function Progress({ label }: { label: string }) {
  return (
    <div className="space-y-2" aria-live="polite">
      <div className="h-[3px] w-full overflow-hidden rounded-full bg-muted">
        <div className="progress-sweep h-full w-full" />
      </div>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export function SectionTitle({ children, aside }: { children: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-baseline justify-between border-t border-border pt-4">
      <h2 className="text-lg font-medium tracking-tight">{children}</h2>
      {aside && <div className="text-sm text-muted-foreground">{aside}</div>}
    </div>
  );
}
