"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { PageHeader } from "../components/PageHeader";
import { LoadingSpinner } from "../components/LoadingSpinner";
import { ErrorDisplay } from "../components/ErrorDisplay";

export default function Tokens() {
  const [data, setData] = useState<any>({
    by_task: [],
    heatmap: [],
    capo: {},
  });
  const [raw, setRaw] = useState<any[]>([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [tok, cpo, r] = await Promise.all([
        api<any>("/dashboard/tokens"),
        api<any>("/dashboard/capo"),
        api<any>(
          `/dashboard/tokens/raw?start_date=${startDate}&end_date=${endDate}`
        ),
      ]);
      setData({
        by_task: tok.by_task || [],
        heatmap: tok.heatmap || [],
        capo: cpo.summary || {},
      });
      setRaw(r.rows || []);
      setError(null);
    } catch (e: any) {
      setData({ by_task: [], heatmap: [], capo: {} });
      setRaw([]);
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate]);

  useEffect(() => {
    load();
  }, [load]);

  const downloadCSV = () => {
    if (!raw.length) return;
    const keys = Object.keys(raw[0]);
    const csv = [
      keys.join(","),
      ...raw.map((row) =>
        keys.map((k) => JSON.stringify(row[k] ?? "")).join(",")
      ),
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tokens.csv";
    a.click();
  };

  if (loading) return <LoadingSpinner text="Loading token data..." />;
  if (error) return <ErrorDisplay error={error} onRetry={load} />;

  const capo = data.capo || {};

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto space-y-8">
      <PageHeader title="Token Analytics" description="FinOps dashboard" />

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-4">
          <div className="text-xs uppercase tracking-widest text-white/40 mb-1">
            Total Tokens
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {(capo.total_tokens || 0).toLocaleString()}
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="text-xs uppercase tracking-widest text-white/40 mb-1">
            Accepted Tasks
          </div>
          <div className="text-2xl font-bold text-success font-mono">
            {capo.accepted_tasks || 0}
          </div>
        </div>
        <div className="glass-panel p-4">
          <div className="text-xs uppercase tracking-widest text-white/40 mb-1">
            CAPO
          </div>
          <div className="text-2xl font-bold text-accent font-mono">
            {capo.capo || 0}
          </div>
        </div>
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold">
            By Task
          </h2>
          <div className="flex gap-2 items-center">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="text-xs bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-white/70"
              aria-label="Start date"
            />
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="text-xs bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-white/70"
              aria-label="End date"
            />
            <button
              onClick={downloadCSV}
              className="text-xs px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:bg-white/10 transition-colors"
            >
              CSV
            </button>
          </div>
        </div>

        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 uppercase text-[11px] tracking-wider border-b border-white/5">
                  <th className="py-2 px-4 font-medium">Task</th>
                  <th className="py-2 px-4 font-medium">Tokens</th>
                  <th className="py-2 px-4 font-medium">Accepted</th>
                </tr>
              </thead>
              <tbody>
                {data.by_task.map((t: any) => (
                  <tr
                    key={t.task_id}
                    className="border-t border-white/5 hover:bg-white/[0.02]"
                  >
                    <td className="py-2 px-4 font-mono text-xs text-accent">
                      {t.task_id}
                    </td>
                    <td className="py-2 px-4 font-mono text-white/70">
                      {t.total_tokens?.toLocaleString() || 0}
                    </td>
                    <td className="py-2 px-4">
                      {t.accepted ? (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-success/20 text-success">
                          YES
                        </span>
                      ) : (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-white/30">
                          NO
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {data.heatmap.length > 0 && (
        <section>
          <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold mb-3">
            Agent-Tool Heatmap
          </h2>
          <div className="glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-white/40 uppercase text-[11px] tracking-wider border-b border-white/5">
                    <th className="py-2 px-4 font-medium">Agent</th>
                    <th className="py-2 px-4 font-medium">Tool</th>
                    <th className="py-2 px-4 font-medium">Tokens</th>
                    <th className="py-2 px-4 font-medium">Calls</th>
                  </tr>
                </thead>
                <tbody>
                  {data.heatmap.map((h: any, i: number) => (
                    <tr
                      key={`${h.agent}-${h.tool}-${i}`}
                      className="border-t border-white/5 hover:bg-white/[0.02]"
                    >
                      <td className="py-2 px-4 text-white/80">{h.agent}</td>
                      <td className="py-2 px-4 font-mono text-xs text-accent">
                        {h.tool}
                      </td>
                      <td className="py-2 px-4 font-mono text-white/70">
                        {h.tokens?.toLocaleString() || 0}
                      </td>
                      <td className="py-2 px-4 font-mono text-white/50">
                        {h.count || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
