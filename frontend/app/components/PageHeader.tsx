"use client";

interface PageHeaderProps {
  title: string;
  description?: string;
  children?: React.ReactNode;
}

export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
      <div>
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white">
          {title}
        </h1>
        {description && (
          <p className="text-white/50 text-sm mt-1">{description}</p>
        )}
      </div>
      {children}
    </header>
  );
}
