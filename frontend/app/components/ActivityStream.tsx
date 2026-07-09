"use client";

import { useEffect } from "react";
import { Activity, Cpu } from "lucide-react";
import { useStore } from "../../lib/store";

export function ActivityStream({ initialActivity }: { initialActivity: any[] }) {
  const { logs, addLog, connectWebSockets } = useStore();

  useEffect(() => {
    // initialize state
    if (logs.length === 0 && initialActivity.length > 0) {
      initialActivity.forEach(log => addLog(log));
    }
    connectWebSockets();
  }, []);

  const displayLogs = logs.length > 0 ? logs : initialActivity;

  const handleExportCSV = () => {
    if (displayLogs.length === 0) return;
    const header = ["Time", "Agent", "Tool", "Status", "Detail"].join(",");
    const rows = displayLogs.map(a => {
      return [
        `"${a.ts}"`,
        `"${a.agent}"`,
        `"${a.tool}"`,
        `"${a.ok ? "Success" : "Failed"}"`,
        `"${a.detail?.replace(/"/g, '""') || ""}"`
      ].join(",");
    });
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-log-${new Date().toISOString()}.csv`;
    a.click();
  };

  return (
    <section className="glass-panel overflow-hidden h-full">
      <div className="p-6 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
        <h2 className="text-sm uppercase tracking-widest text-white/50 font-semibold flex items-center gap-2">
          <Activity className="w-4 h-4" /> Activity Stream
        </h2>
        <button onClick={handleExportCSV} className="text-xs bg-white/10 hover:bg-white/20 px-3 py-1 rounded transition-colors">
          Export CSV
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase text-white/30 bg-white/[0.01]">
            <tr>
              <th className="px-6 py-4 font-medium tracking-wider">Time</th>
              <th className="px-6 py-4 font-medium tracking-wider">Agent</th>
              <th className="px-6 py-4 font-medium tracking-wider">Tool</th>
              <th className="px-6 py-4 font-medium tracking-wider">Status</th>
              <th className="px-6 py-4 font-medium tracking-wider">Detail</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {displayLogs.map((a: any) => (
              <tr key={a.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-white/40 font-mono text-xs">{a.ts}</td>
                <td className="px-6 py-4">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 text-white/80 text-xs font-medium">
                    <Cpu className="w-3 h-3 text-accent" /> {a.agent}
                  </span>
                </td>
                <td className="px-6 py-4 text-white/70 font-medium">{a.tool}</td>
                <td className="px-6 py-4">
                  {a.ok ? (
                    <span className="inline-flex items-center gap-1.5 text-success text-xs font-medium bg-success/10 px-2 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span> Success
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 text-danger text-xs font-medium bg-danger/10 px-2 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-danger"></span> Failed
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 text-white/50 max-w-xs truncate" title={a.detail}>
                  {a.detail}
                </td>
              </tr>
            ))}
            {displayLogs.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-16 text-center">
                  <div className="flex flex-col items-center gap-2 opacity-40">
                    <Activity className="w-8 h-8 mb-2" />
                    <p>No activity recorded yet.</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
