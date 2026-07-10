import { api } from "@/lib/api";
import { Clock, AlertTriangle, CheckCircle, Database } from "lucide-react";

export default async function Task({ params }: { params: { id: string } }) {
  const task = await api<any>(`/dashboard/task/${params.id}`);
  if (!task) return <div style={{ padding: 24, color: "#f85149" }}>Failed to load task.</div>;

  return (
    <main style={{ padding: 24, maxWidth: 800, margin: "0 auto" }}>
      <h1 style={{ borderBottom: "1px solid #30363d", paddingBottom: 12 }}>Task Lifecycle: {params.id}</h1>
      
      <section style={{ marginTop: 24 }}>
        <h2 style={{ fontSize: 18, display: "flex", alignItems: "center", gap: 8 }}><Clock size={18} /> Trajectory</h2>
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 16, marginTop: 12 }}>
          {task.spans.map((s: any) => (
            <div key={s.id} style={{ padding: "8px 0", borderBottom: "1px solid #21262d", display: "flex", alignItems: "start", gap: 12 }}>
              <span style={{ color: "#8b949e", fontFamily: "monospace", fontSize: 12, marginTop: 2 }}>{s.ts.split(" ")[1]}</span>
              <div>
                <div style={{ color: s.ok ? "#c9d1d9" : "#f85149", fontWeight: 500 }}>
                  [{s.agent}] {s.tool} {s.ok ? "✓" : "✕"}
                </div>
                <div style={{ color: "#8b949e", fontSize: 13, marginTop: 4 }}>{s.detail}</div>
              </div>
            </div>
          ))}
          {task.spans.length === 0 && <div style={{ color: "#8b949e" }}>No spans recorded.</div>}
        </div>
      </section>

      {task.hitl.length > 0 && (
        <section style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 18, display: "flex", alignItems: "center", gap: 8 }}><AlertTriangle size={18} color="#d29922" /> HITL Reviews</h2>
          <div style={{ display: "grid", gap: 12, marginTop: 12 }}>
            {task.hitl.map((h: any) => (
              <div key={h.id} style={{ background: "#21262d", padding: 12, borderRadius: 6 }}>
                <strong>Status:</strong> {h.status} <span style={{ color: "#8b949e", marginLeft: 12 }}>{h.ts}</span>
                {h.resolution && <div style={{ marginTop: 8, fontStyle: "italic" }}>Resolution: {h.resolution}</div>}
              </div>
            ))}
          </div>
        </section>
      )}

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18, display: "flex", alignItems: "center", gap: 8 }}><Database size={18} /> Token Ledger</h2>
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 16, marginTop: 12 }}>
          {task.tokens.map((t: any, i: number) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
              <span>{t.agent} ({t.model})</span>
              <span style={{ color: "#3fb950" }}>${t.cost_usd.toFixed(4)} ({t.input_tokens} in / {t.output_tokens} out)</span>
            </div>
          ))}
          {task.tokens.length === 0 && <div style={{ color: "#8b949e" }}>No token spend recorded.</div>}
        </div>
      </section>

      {task.crashes.length > 0 && (
        <section style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 18, display: "flex", alignItems: "center", gap: 8 }}><AlertTriangle size={18} color="#f85149" /> Crashes / Hibernation</h2>
          <div style={{ background: "#f8514922", border: "1px solid #f85149", borderRadius: 6, padding: 16, marginTop: 12 }}>
            {task.crashes.map((c: any, i: number) => (
              <div key={i}>
                <strong>{c.reason}</strong> at {c.created_at}
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
