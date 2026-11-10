export function SoftLoader({
  label = "Loading",
  compact = false,
}: {
  label?: string;
  compact?: boolean;
}) {
  if (compact) {
    return (
      <div className="flex items-center justify-center py-10" role="status" aria-label={label}>
        <div className="boot-spinner h-8 w-8" />
        <span className="sr-only">{label}</span>
      </div>
    );
  }

  return (
    <div className="relative flex min-h-[50vh] items-center justify-center overflow-hidden px-6">
      <div className="relative flex flex-col items-center text-center">
        <p className="text-[0.7rem] font-semibold uppercase tracking-[0.18em] text-[var(--accent)]">
          AI Job Hunter
        </p>
        <div className="boot-spinner mt-6 h-10 w-10" aria-hidden />
        <span className="sr-only">{label}</span>
      </div>
    </div>
  );
}
