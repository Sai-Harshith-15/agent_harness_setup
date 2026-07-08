import { api } from "@/lib/api";

export default async function Vault({ searchParams }: { searchParams: { path?: string } }) {
  const path = searchParams.path || "";
  const data = await api<any>(`/dashboard/vault${path ? `?path=${encodeURIComponent(path)}` : ""}`)
    .catch(() => ({ entries: [], note: null }));
  return (
    <main style={{ padding: 24 }}>
      <h1>Vault <span style={{ fontSize: 12, opacity: 0.6 }}>(read-only)</span></h1>
      {data.note ? (
        <pre style={{ background: "#161b22", padding: 12, borderRadius: 6, whiteSpace: "pre-wrap" }}>
{data.note.content}
        </pre>
      ) : (
        <ul>{(data.entries || []).map((e: string) => (
          <li key={e}><a href={`/vault?path=${encodeURIComponent(e)}`} style={{ color: "#58a6ff" }}>{e}</a></li>
        ))}</ul>
      )}
    </main>
  );
}
