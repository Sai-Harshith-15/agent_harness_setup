"use client";

import { useEffect, useState, useCallback } from "react";
import { DiffEditor } from "@monaco-editor/react";
import { api } from "@/lib/api";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorDisplay } from "../components/ErrorDisplay";

export default function Hitl() {
  const [items, setItems] = useState<any[]>([]);
  const [active, setActive] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await api<any>("/dashboard/hitl");
      setItems(data.open || []);
      setError(null);
    } catch (e: any) {
      setItems([]);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [load]);

  async function resolve(status: string) {
    try {
      await fetch("/api/dashboard/hitl", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          item_id: active.id,
          status,
          resolution: status,
        }),
      });
    } catch (e) {
      // continue
    }
    setActive(null);
    load();
  }

  const diffObj = active?.proposed_diff
    ? JSON.parse(active.proposed_diff)
    : { before: "", after: "" };

  if (loading) return <LoadingSpinner text="Loading HITL queue..." />;
  if (error) return <ErrorDisplay error={error} onRetry={load} />;

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <PageHeader
        title="HITL Queue"
        description="Human-in-the-loop clarification requests"
      />

      {items.length === 0 ? (
        <div className="glass-panel p-8 text-center">
          <p className="text-white/40">Nothing awaiting a human.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((it) => (
            <div
              key={it.id}
              className="glass-panel p-4 hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm font-bold text-accent">
                  {it.agent}
                </span>
                <span className="text-xs text-white/30 font-mono">
                  task {it.task_id}
                </span>
              </div>
              <p className="text-sm text-white/70 mb-3">{it.question}</p>
              <button
                onClick={() => setActive(it)}
                className="text-xs px-3 py-1.5 rounded-lg bg-white/10 border border-white/10 text-white/70 hover:bg-white/20 transition-colors"
              >
                Review Diff
              </button>
            </div>
          ))}
        </div>
      )}

      {active && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={(e) => {
            if (e.target === e.currentTarget) setActive(null);
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") setActive(null);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Review proposed change"
            className="bg-[#0d1117] border border-white/20 rounded-xl p-6 w-[85vw] max-w-5xl max-h-[90vh] flex flex-col"
          >
            <h3 className="text-lg font-bold text-white mb-4">
              Proposed Change: {diffObj.path || "unknown"}
            </h3>
            <div className="flex-1 min-h-0" style={{ height: "55vh" }}>
              <DiffEditor
                height="100%"
                original={diffObj.before}
                modified={diffObj.after}
                theme="vs-dark"
                options={{ readOnly: true, minimap: { enabled: false } }}
              />
            </div>
            <div className="flex gap-3 mt-4 justify-end">
              <button
                onClick={() => setActive(null)}
                className="px-4 py-2 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 transition-colors"
              >
                Close
              </button>
              <button
                onClick={() => resolve("rejected")}
                className="px-4 py-2 rounded-lg bg-danger/20 border border-danger/30 text-danger hover:bg-danger/30 transition-colors"
              >
                Reject
              </button>
              <button
                onClick={() => resolve("modified")}
                className="px-4 py-2 rounded-lg bg-warning/20 border border-warning/30 text-warning hover:bg-warning/30 transition-colors"
              >
                Modify
              </button>
              <button
                onClick={() => resolve("approved")}
                className="px-4 py-2 rounded-lg bg-success/20 border border-success/30 text-success hover:bg-success/30 transition-colors"
              >
                Approve
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
