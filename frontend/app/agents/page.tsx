import { api } from "@/lib/api";

export default async function Agents() {
  const data = await api<any>("/dashboard/agents");
  return (
    <main style={{ padding: 24 }}>
      <h1>Agents <span style={{ fontSize: 13, opacity: 0.6 }}>· orchestrator: {data.orchestrator}</span></h1>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 12 }}>
        {data.agents.map((a: any) => (
          <div key={a.id} style={{ border: "1px solid #21262d", borderRadius: 8, padding: 12 }}>
            <h3 style={{ margin: 0 }}>{a.id} {a.role === "orchestrator" && "★"}</h3>
            <div style={{ fontSize: 12, opacity: 0.7 }}>role: {a.role} · adapter: {a.adapter}</div>
            <div style={{ fontSize: 12, marginTop: 6 }}>caps: {(a.capabilities || []).join(", ")}</div>
          </div>
        ))}
      </div>
    </main>
  );
}
