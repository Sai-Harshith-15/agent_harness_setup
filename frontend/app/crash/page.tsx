"use client";
import { useEffect, useState } from "react";

export default function Crash() {
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    fetch("http://127.0.0.1:27180/dashboard/crashes")
      .then(r => { if (!r.ok) throw new Error("Failed to load crashes"); return r.json(); })
      .then(d => { setData(d); setError(null); })
      .catch(e => { setData({ released_locks: [], hibernated_orphans: [] }); setError(e.message); });
  };

  useEffect(() => {
    load();
  }, []);

  const handleRerun = async (taskId: string) => {
    await fetch(`http://127.0.0.1:27180/dashboard/crashes/${taskId}/rerun`, { method: "POST" });
    load();
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Crash reconciliation</h1>
      {error && <div style={{ color: "#ff7b72", padding: "12px 0" }}>Backend Error: {error}</div>}
      <h2 style={{ fontSize: 16 }}>Released locks (crash_recovery)</h2>
      <ul>
        {data.released_locks.map((l: any, i: number) => (
          <li key={i}>{l.resource} — was {l.was}</li>
        ))}
      </ul>
      {data.released_locks.length === 0 && <p style={{ opacity: 0.6 }}>No orphaned leases.</p>}
      
      <h2 style={{ fontSize: 16, marginTop: 16 }}>Hibernated orphans</h2>
      <ul>
        {data.hibernated_orphans.map((o: any) => (
          <li key={o.task_id} style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 8 }}>
            <span>{o.task_id} — {o.reason}</span>
            <button onClick={() => handleRerun(o.task_id)} style={{ padding: "4px 8px", cursor: "pointer", fontSize: 12, borderRadius: 4, background: "#1f6feb", border: "none", color: "#fff" }}>
              Re-run
            </button>
          </li>
        ))}
      </ul>
      {data.hibernated_orphans.length === 0 && <p style={{ opacity: 0.6 }}>No hibernated orphans.</p>}
    </main>
  );
}
