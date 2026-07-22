import { api } from "@/lib/api";
import { PageHeader } from "../components/PageHeader";
import { DataCard } from "../components/DataCard";

export default async function Vault({
  searchParams,
}: {
  searchParams: { path?: string };
}) {
  const path = searchParams.path || "";
  const data = await api<any>(
    `/dashboard/vault${path ? `?path=${encodeURIComponent(path)}` : ""}`
  );

  const hasError = data.error || data.entries === null;
  const entries: string[] = data.entries?.files || data.entries || [];

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <PageHeader title="Vault" description="Read-only Obsidian browser" />
      {hasError ? (
        <DataCard title="Unavailable">
          <div className="text-sm text-white/40 py-8 text-center space-y-2">
            <p>{data.error || "Obsidian backend is unreachable."}</p>
            <p className="text-xs text-white/25">
              Check that the obsidian-local-rest-api plugin is running on port 27123.
            </p>
          </div>
        </DataCard>
      ) : data.note ? (
        <DataCard title={path}>
          <pre className="text-sm text-white/80 whitespace-pre-wrap font-mono bg-black/20 rounded-lg p-4 overflow-x-auto max-h-[70vh] overflow-y-auto">
            {data.note.content}
          </pre>
        </DataCard>
      ) : (
        <DataCard title="Directory">
          <ul className="space-y-1">
            {(entries || []).map((e: string) => (
              <li key={e}>
                <a
                  href={`/vault?path=${encodeURIComponent(e)}`}
                  className="text-accent hover:text-white transition-colors text-sm font-mono block py-1.5 px-3 rounded-lg hover:bg-white/5"
                >
                  {e}
                </a>
              </li>
            ))}
            {(entries || []).length === 0 && (
              <p className="text-sm text-white/30 py-4 text-center">
                No entries found
              </p>
            )}
          </ul>
        </DataCard>
      )}
    </main>
  );
}
