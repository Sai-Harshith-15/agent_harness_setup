import { api } from "@/lib/api";

export default async function Task({ params }: { params: { id: string } }) {
  const state = await api<any>("/dashboard/state").catch(() => ({ recent_activity: [] }));
  const spans = state.recent_activity.filter((a: any) => a.task_id === params.id);
  return (
    <main style={{ padding: 24 }}>
      <h1>Task {params.id}</h1>
      <h2 style={{ fontSize: 16 }}>Trajectory</h2><ol>
        {spans.map((s: any) => (
          <li key={s.id} style={{ margin: "6px 0", color: s.ok ? "#e6edf3" : "#f85149" }}>
            <code>{s.ts}</code> · {s.agent} · <strong>{s.tool}</strong> {s.ok ? "✓" : "✕"} — {s.detail}
          </li>
        ))}
        {spans.length === 0 && <p style={{ opacity: 0.6 }}>No spans recorded for this task.</p>}
      </ol>
    </main>
  );
}
