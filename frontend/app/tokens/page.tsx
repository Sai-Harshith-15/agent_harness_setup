import { api } from "@/lib/api";

export default async function Tokens() {
  const [tok, capo] = await Promise.all([
    api<any>("/dashboard/tokens").catch(() => ({ by_task: [], heatmap: [] })),
    api<any>("/dashboard/capo").catch(() => ({ summary: {}, trend: [] })),
  ]);
  return (
    <main style={{ padding: 24 }}>
      <h1>Token analytics</h1>
      <p>CAPO: <strong>{capo.summary?.capo ?? "n/a"}</strong> tokens/accepted
         ({capo.summary?.accepted_tasks ?? 0} accepted, {capo.summary?.total_tokens ?? 0} total)</p>

      <h2 style={{ fontSize: 16 }}>Top tasks by spend</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead><tr style={{ textAlign: "left", opacity: 0.6 }}><th>task</th><th>tokens</th><th>accepted</th></tr></thead>
        <tbody>
          {tok.by_task.map((t: any) => (
            <tr key={t.task_id} style={{ borderTop: "1px solid #21262d" }}>
              <td style={{ padding: "6px 8px" }}><a href={`/task/${t.task_id}`} style={{ color: "#58a6ff" }}>{t.task_id}</a></td>
              <td>{t.total_tokens}</td><td>{t.accepted ? "✓" : "…"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ fontSize: 16, marginTop: 24 }}>Agent × tool heatmap</h2><ul>{tok.heatmap.map((h: any, i: number) => <li key={i}>{h.agent} · {h.tool}: {h.tokens} tok</li>)}</ul>
    </main>
  );
}
