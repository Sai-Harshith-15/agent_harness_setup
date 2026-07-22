"use client";

import { useEffect } from "react";
import { useStore } from "../../lib/store";

export function ActivityStream({ initialActivity }: { initialActivity: any[] }) {
  const { logs, addLog, connectWebSockets } = useStore();

  useEffect(() => {
    if (logs.length === 0 && initialActivity.length > 0) {
      initialActivity.forEach((log) => addLog(log));
    }
    const cleanup = connectWebSockets();
    return cleanup;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const displayLogs = logs.length > 0 ? logs : initialActivity;

  const handleExportCSV = () => {
    if (displayLogs.length === 0) return;
    const header = ["Time", "Agent", "Tool", "Status", "Detail"].join(",");
    const rows = displayLogs.map((a) =>
      [
        `"${a.ts}"`,
        `"${a.agent}"`,
        `"${a.tool}"`,
        `"${a.ok ? "Success" : "Failed"}"`,
        `"${a.detail?.replace(/"/g, '""') || ""}"`,
      ].join(",")
    );
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `audit-log-${new Date().toISOString()}.csv`;
    a.click();
  };

  return (
    <section className="glass-panel flex flex-col h-full min-h-[400px]">
      <div className="p-4 border-b border-white/5 bg-white/[0.02] flex items-center justify-between">
        <h2 className="text-sm uppercase tracking-widest text-white/50 font-semibold">
          Activity Stream
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-white/30 font-mono">
            {displayLogs.length} events
          </span>
          <button
            onClick={handleExportCSV}
            className="text-xs px-3 py-1 rounded-lg bg-white/5 border border-white/10 text-white/60 hover:text-white/90 hover:bg-white/10 transition-colors"
          >
            Export CSV
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">
        {displayLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <p className="text-sm text-white/40">No activity yet.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-[#0a0a0a]/95 backdrop-blur-sm">
              <tr className="text-left text-white/40 uppercase text-[11px] tracking-wider">
                <th className="py-2 px-4 font-medium">Time</th>
                <th className="py-2 px-4 font-medium">Agent</th>
                <th className="py-2 px-4 font-medium">Tool</th>
                <th className="py-2 px-4 font-medium">Status</th>
                <th className="py-2 px-4 font-medium">Detail</th>
              </tr>
            </thead>
            <tbody>
              {displayLogs.map((a, i) => (
                <tr
                  key={`${a.id}_${i}`}
                  className="border-t border-white/5 hover:bg-white/[0.02] transition-colors"
                >
                  <td className="py-2 px-4 font-mono text-xs text-white/50">
                    {a.ts}
                  </td>
                  <td className="py-2 px-4 text-white/80 font-medium">
                    {a.agent}
                  </td>
                  <td className="py-2 px-4 font-mono text-xs text-accent">
                    {a.tool}
                  </td>
                  <td className="py-2 px-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                        a.ok
                          ? "bg-success/20 text-success"
                          : "bg-danger/20 text-danger"
                      }`}
                    >
                      {a.ok ? "OK" : "FAIL"}
                    </span>
                  </td>
                  <td className="py-2 px-4 text-xs text-white/40 max-w-[200px] truncate">
                    {a.detail || "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
