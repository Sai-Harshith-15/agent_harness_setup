import { api } from "@/lib/api";

export default async function Crash() {
  const data = await api<any>("/dashboard/crashes").catch(() => ({ released_locks: [], hibernated_orphans: [] }));
  return (
    <main style={{ padding: 24 }}>
      <h1>Crash reconciliation</h1>
      <h2 style={{ fontSize: 16 }}>Released locks (crash_recovery)</h2><ul>{data.released_locks.map((l: any, i: number) => <li key={i}>{l.resource} — was {l.was}</li>)}</ul>
      {data.released_locks.length === 0 && <p style={{ opacity: 0.6 }}>No orphaned leases.</p>}
      <h2 style={{ fontSize: 16, marginTop: 16 }}>Hibernated orphans</h2><ul>{data.hibernated_orphans.map((o: any) => <li key={o.task_id}>{o.task_id} — {o.reason}</li>)}</ul>
    </main>
  );
}
