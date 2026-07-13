"use client";

interface ErrorDisplayProps {
  error: string;
  onRetry?: () => void;
}

export function ErrorDisplay({ error, onRetry }: ErrorDisplayProps) {
  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <div className="glass-panel p-8 border border-danger/30">
        <h2 className="text-lg font-bold text-danger mb-3">Backend Error</h2>
        <pre className="text-sm text-white/60 whitespace-pre-wrap font-mono bg-black/30 p-3 rounded-lg">
          {error}
        </pre>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-4 px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white/80 hover:bg-white/20 transition-colors"
          >
            Retry
          </button>
        )}
      </div>
    </main>
  );
}
