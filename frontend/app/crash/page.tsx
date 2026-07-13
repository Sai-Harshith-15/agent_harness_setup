"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorDisplay } from "../components/ErrorDisplay";

export default function Crash() {
  const [data, setData] = useState<{
    released_locks: any[];
    hibernated_orphans: any[];
  }>({ released_locks: [], hibernated_orphans: [] });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const d = await api<any>("/dashboard/crashes");
      setData(d);
      setError(null);
    } catch (e: any) {
      setData({ released_locks: [], hibernated_orphans: [] });
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleRerun = async (taskId: string) => {
    try {
      await fetch(`/api/dashboard/crashes/${taskId}/rerun`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
    } catch (e) {
      // continue
    }
    load();
  };

  if (loading) return <LoadingSpinner text="Loading crash data..." />;
  if (error) return <ErrorDisplay error={error} onRetry={load} />;

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <PageHeader
        title="Crash Reconciliation"
        description="Recovered locks and orphaned tasks"
      />

      <div className="space-y-8">
        <section>
          <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold mb-3">
            Released Locks (crash recovery)
          </h2>
          {data.released_locks.length === 0 ? (
            <p className="text-sm text-white/30 glass-panel p-4">
              No orphaned leases.
            </p>
          ) : (
            <div className="space-y-2">
              {data.released_locks.map((l: any, i: number) => (
                <div key={i} className="glass-panel p-3 text-sm">
                  <span className="font-mono text-accent">{l.resource}</span>
                  <span className="text-white/40 ml-3">was {l.was}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        <section>
          <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold mb-3">
            Hibernated Orphans
          </h2>
          {data.hibernated_orphans.length === 0 ? (
            <p className="text-sm text-white/30 glass-panel p-4">
              No hibernated orphans.
            </p>
          ) : (
            <div className="space-y-2">
              {data.hibernated_orphans.map((o: any) => (
                <div
                  key={o.task_id}
                  className="glass-panel p-3 flex items-center justify-between"
                >
                  <div className="text-sm">
                    <span className="font-mono text-accent">
                      {o.task_id}
                    </span>
                    <span className="text-white/40 ml-3">
                      {o.reason}
                    </span>
                  </div>
                  <button
                    onClick={() => handleRerun(o.task_id)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-accent/20 border border-accent/30 text-accent hover:bg-accent/30 transition-colors"
                  >
                    Re-run
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
