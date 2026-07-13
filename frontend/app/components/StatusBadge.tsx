interface StatusBadgeProps {
  status: string;
  ok?: boolean;
  degraded?: boolean;
}

export function StatusBadge({ status, ok, degraded }: StatusBadgeProps) {
  const color = ok ? "bg-success" : degraded ? "bg-warning" : "bg-danger";
  return (
    <div className="glass-panel px-4 py-3 flex items-center gap-3 border border-white/5">
      <div className="relative flex items-center justify-center h-3 w-3">
        <span
          className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${color}`}
        />
        <span className={`relative inline-flex rounded-full h-2 w-2 ${color}`} />
      </div>
      <span className="uppercase tracking-widest text-xs font-bold text-white/80">
        {status}
      </span>
    </div>
  );
}
