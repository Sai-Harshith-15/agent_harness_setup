"use client";
import { useEffect, useState } from "react";
import { DiffEditor } from "@monaco-editor/react";

export default function Hitl() {
  const [items, setItems] = useState<any[]>([]);
  const [active, setActive] = useState<any | null>(null);

  const [error, setError] = useState<string | null>(null);

  const load = () => fetch("http://127.0.0.1:27180/dashboard/hitl")
    .then((r) => { if (!r.ok) throw new Error("Failed to load"); return r.json(); })
    .then((d) => { setItems(d.open || []); setError(null); })
    .catch((e) => { setItems([]); setError(e.message); });
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);

  async function resolve(status: string) {
    await fetch("http://127.0.0.1:27180/dashboard/hitl", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: active.id, status, resolution: status }),
    });
    setActive(null); load();
  }

  const diffObj = active?.proposed_diff ? JSON.parse(active.proposed_diff) : { before: "", after: "" };

  return (
    <main style={{ padding: 24 }}>
      <h1>HITL queue</h1>
      {error && <div style={{ color: "#ff7b72", padding: "12px 0" }}>Backend Error: {error}</div>}
      {!error && items.length === 0 && <p style={{ opacity: 0.6 }}>Nothing awaiting a human.</p>}
      {items.map((it) => (
        <div key={it.id} style={{ border: "1px solid #21262d", borderRadius: 8, padding: 12, margin: "8px 0" }}>
          <div><strong>{it.agent}</strong> · task {it.task_id}</div>
          <div style={{ margin: "6px 0" }}>{it.question}</div>
          <button onClick={() => setActive(it)} style={{ cursor: "pointer" }}>Review diff</button>
        </div>
      ))}

      {active && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", display: "grid", placeItems: "center" }}>
          <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 10, padding: 20, width: "80vw" }}>
            <h3>Proposed change: {diffObj.path}</h3>
            <div style={{ height: "60vh", marginTop: "12px" }}>
              <DiffEditor
                height="100%"
                original={diffObj.before}
                modified={diffObj.after}
                theme="vs-dark"
                options={{ readOnly: true, minimap: { enabled: false } }}
              />
            </div>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button onClick={() => resolve("approved")}>Approve</button>
              <button onClick={() => resolve("modified")}>Modify</button>
              <button onClick={() => resolve("rejected")}>Reject</button>
              <button onClick={() => setActive(null)} style={{ marginLeft: "auto" }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
