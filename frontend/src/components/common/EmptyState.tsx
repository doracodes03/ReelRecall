type EmptyStateProps = {
  title: string;
  description?: string;
};

export default function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--rr-border)] bg-white/80 p-8 text-center">
      <h3 className="text-lg font-bold text-[var(--rr-text)]">{title}</h3>
      {description ? <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[var(--rr-muted)]">{description}</p> : null}
    </div>
  );
}
