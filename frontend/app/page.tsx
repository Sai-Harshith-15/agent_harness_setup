async function getHealth() {
  try {
    const res = await fetch("http://127.0.0.1:27180/health", { cache: "no-store" });
    return await res.json();
  } catch {
    return { status: "unreachable", obsidian_backend: false };
  }
}

async function getState() {
  try {
    const res = await fetch("http://127.0.0.1:27180/dashboard/state", { cache: "no-store" });
    return await res.json();
  } catch {
    return { locks: [], recent_activity: [] };
  }
}

export default async function Home() {
  const [health, state] = await Promise.all([getHealth(), getState()]);
  const ok = health.status === "ok";
  const color = ok ? "#3fb950" : health.status === "degraded" ? "#d29922" : "#f85149";

  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: 28 }}>Agentic OS — Mission Control</h1>
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 0" }}>
        <span style={{ width: 12, height: 12, borderRadius: 999, background: color }} />
        <strong style={{ textTransform: "uppercase", letterSpacing: 1 }}>{health.status}</strong>
        <span style={{ opacity: 0.7 }}>· Obsidian backend: {health.obsidian_backend ? "reachable" : "down"}</span>
      </div>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18, opacity: 0.9 }}>Active locks</h2>
        {state.locks.length === 0
          ? <p style={{ opacity: 0.6 }}>None held.</p>
          : <ul>{state.locks.map((l: any) => <li key={l.resource}>{l.resource} — {l.agent}:{l.task_id}</li>)}</ul>}
      </section>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18, opacity: 0.9 }}>Recent activity</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", opacity: 0.6 }}>
              <th style={{ padding: "6px 8px" }}>ts</th><th>agent</th><th>tool</th><th>ok</th><th>detail</th>
            </tr>
          </thead>
          <tbody>
            {state.recent_activity.map((a: any) => (
              <tr key={a.id} style={{ borderTop: "1px solid #21262d" }}>
                <td style={{ padding: "6px 8px", whiteSpace: "nowrap" }}>{a.ts}</td>
                <td>{a.agent}</td><td>{a.tool}</td>
                <td style={{ color: a.ok ? "#3fb950" : "#f85149" }}>{a.ok ? "✓" : "✕"}</td>
                <td style={{ opacity: 0.8 }}>{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
