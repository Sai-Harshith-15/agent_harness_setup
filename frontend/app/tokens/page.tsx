"use client";
import { useEffect, useState } from "react";

export default function Tokens() {
  const [data, setData] = useState<any>({ by_task: [], heatmap: [], capo: {} });
  const [raw, setRaw] = useState<any[]>([]);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    Promise.all([
      fetch("http://127.0.0.1:27180/dashboard/tokens").then(r => { if (!r.ok) throw new Error(`tokens -> ${r.status}`); return r.json(); }),
      fetch("http://127.0.0.1:27180/dashboard/capo").then(r => { if (!r.ok) throw new Error(`capo -> ${r.status}`); return r.json(); }),
      fetch(`http://127.0.0.1:27180/dashboard/tokens/raw?start_date=${startDate}&end_date=${endDate}`).then(r => { if (!r.ok) throw new Error(`tokens/raw -> ${r.status}`); return r.json(); })
    ]).then(([tok, cpo, r]) => {
      setData({ by_task: tok.by_task || [], heatmap: tok.heatmap || [], capo: cpo.summary || {} });
      setRaw(r.rows || []);
      setError(null);
    }).catch(e => { setData({ by_task: [], heatmap: [], capo: {} }); setRaw([]); setError(e instanceof Error ? e.message : String(e)); });
  };

  useEffect(() => { load(); }, [startDate, endDate]);

  const downloadCSV = () => {
    if (!raw.length) return;
    const keys = Object.keys(raw[0]);
    const csv = [
      keys.join(","),
      ...raw.map(row => keys.map(k => JSON.stringify(row[k] ?? "")).join(","))
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "tokens.csv";
    a.click();
  };

  return (
    <main style={{ padding: 24 }}>
      <h1>Token analytics</h1>
      {error && <div style={{ color: "#ff7b72", padding: "12px 0" }}>Backend Error: {error}</div>}
      <p>CAPO: <strong>{data.capo.capo ?? "n/a"}</strong> tokens/accepted
         ({data.capo.accepted_tasks ?? 0} accepted, {data.capo.total_tokens ?? 0} total)</p>

      <div style={{ display: "flex", gap: 16, marginTop: 24, alignItems: "center" }}>
        <h2 style={{ fontSize: 16, margin: 0 }}>Raw Ledger (SQL View)</h2>
        <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
        <span>to</span>
        <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
        <button onClick={downloadCSV} style={{ cursor: "pointer" }}>Export CSV</button>
      </div>

      <div style={{ height: 300, overflowY: "auto", border: "1px solid #30363d", marginTop: 12 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13, textAlign: "left" }}>
          <thead style={{ position: "sticky", top: 0, background: "#0d1117" }}>
            <tr>
              <th style={{ padding: "4px 8px" }}>id</th>
              <th style={{ padding: "4px 8px" }}>ts</th>
              <th style={{ padding: "4px 8px" }}>agent</th>
              <th style={{ padding: "4px 8px" }}>task_id</th>
              <th style={{ padding: "4px 8px" }}>tool</th>
              <th style={{ padding: "4px 8px" }}>in</th>
              <th style={{ padding: "4px 8px" }}>out</th>
              <th style={{ padding: "4px 8px" }}>acc</th>
            </tr>
          </thead>
          <tbody>
            {raw.map(r => (
              <tr key={r.id} style={{ borderTop: "1px solid #21262d" }}>
                <td style={{ padding: "4px 8px" }}>{r.id}</td>
                <td style={{ padding: "4px 8px" }}>{r.ts}</td>
                <td style={{ padding: "4px 8px" }}>{r.agent}</td>
                <td style={{ padding: "4px 8px" }}>{r.task_id}</td>
                <td style={{ padding: "4px 8px" }}>{r.tool}</td>
                <td style={{ padding: "4px 8px" }}>{r.tokens_in}</td>
                <td style={{ padding: "4px 8px" }}>{r.tokens_out}</td>
                <td style={{ padding: "4px 8px" }}>{r.accepted}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 style={{ fontSize: 16, marginTop: 24 }}>Top tasks by spend</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead><tr style={{ textAlign: "left", opacity: 0.6 }}><th style={{ padding: "4px 8px" }}>task</th><th style={{ padding: "4px 8px" }}>tokens</th><th style={{ padding: "4px 8px" }}>accepted</th></tr></thead>
        <tbody>
          {data.by_task.map((t: any) => (
            <tr key={t.task_id} style={{ borderTop: "1px solid #21262d" }}>
              <td style={{ padding: "6px 8px" }}><a href={`/task/${t.task_id}`} style={{ color: "#58a6ff" }}>{t.task_id}</a></td>
              <td style={{ padding: "4px 8px" }}>{t.total_tokens}</td><td style={{ padding: "4px 8px" }}>{t.accepted ? "✓" : "…"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ fontSize: 16, marginTop: 24 }}>Agent × tool heatmap</h2>
      <ul>{data.heatmap.map((h: any, i: number) => <li key={i}>{h.agent} · {h.tool}: {h.tokens} tok</li>)}</ul>
    </main>
  );
}
