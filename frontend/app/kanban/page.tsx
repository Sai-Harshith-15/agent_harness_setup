import { api } from "@/lib/api";

type Row = { status: string; id: string; title: string; agent: string; capo: number; tokens: number };
const COLUMNS = ["backlog", "in-progress", "delegated", "awaiting-hitl", "hibernated", "done", "rejected"];

async function getPlan(): Promise<Row[]> {
  return (await api<{ rows: Row[] }>("/dashboard/plan")).rows;
}

export default async function Kanban() {
  const rows = await getPlan();
  return (
    <main style={{ padding: 24 }}>
      <h1>Kanban</h1>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${COLUMNS.length}, 1fr)`, gap: 12 }}>
        {COLUMNS.map((col) => (
          <div key={col} style={{ background: "#0d1117", borderRadius: 8, padding: 8, minHeight: 200 }}>
            <h3 style={{ fontSize: 12, textTransform: "uppercase", opacity: 0.6 }}>{col}</h3>
            {rows.filter((r) => r.status === col).map((r) => (
              <a key={r.id} href={`/task/${r.id}`} style={{ display: "block", background: "#161b22",
                   border: "1px solid #21262d", borderRadius: 6, padding: 8, margin: "8px 0", color: "#e6edf3", textDecoration: "none" }}>
                <div style={{ fontSize: 13 }}>{r.title}</div>
                <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
                  {r.agent} · {r.tokens} tok · CAPO {r.capo}
                </div>
              </a>
            ))}
          </div>
        ))}
      </div>
    </main>
  );
}
