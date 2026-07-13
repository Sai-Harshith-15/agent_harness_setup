export function DataCard({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`glass-panel ${className}`}
    >
      {title && (
        <div className="p-4 border-b border-white/5 bg-white/[0.02]">
          <h2 className="text-sm uppercase tracking-widest text-white/50 font-semibold">
            {title}
          </h2>
        </div>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}
