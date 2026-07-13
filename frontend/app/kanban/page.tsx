import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader } from "../components/PageHeader";
import { DataCard } from "../components/DataCard";

type Row = {
  status: string;
  id: string;
  title: string;
  agent: string;
  capo: number;
  tokens: number;
};
const COLUMNS = [
  "backlog",
  "in-progress",
  "delegated",
  "awaiting-hitl",
  "hibernated",
  "done",
  "rejected",
];

async function getPlan(): Promise<Row[]> {
  return (await api<{ rows: Row[] }>("/dashboard/plan")).rows;
}

const STATUS_COLORS: Record<string, string> = {
  "in-progress": "text-accent",
  done: "text-success",
  rejected: "text-danger",
  "awaiting-hitl": "text-warning",
  hibernated: "text-white/40",
  delegated: "text-white/60",
  backlog: "text-white/50",
};

export default async function Kanban() {
  const rows = await getPlan();

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <PageHeader title="Kanban" description="PLAN.md task board" />
      <DataCard>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {COLUMNS.map((col) => {
            const items = rows.filter((r) => r.status === col);
            const color = STATUS_COLORS[col] || "text-white/50";
            return (
              <div
                key={col}
                className="bg-white/[0.02] border border-white/5 rounded-xl p-3 min-h-[150px]"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3
                    className={`text-[11px] uppercase tracking-wider font-bold ${color}`}
                  >
                    {col}
                  </h3>
                  <span className="text-[10px] font-mono text-white/30 bg-white/5 px-1.5 py-0.5 rounded-full">
                    {items.length}
                  </span>
                </div>
                <div className="space-y-2">
                  {items.map((r) => (
                    <Link
                      key={r.id}
                      href={`/task/${r.id}`}
                      className="block bg-white/5 border border-white/5 rounded-lg p-2.5 hover:bg-white/10 transition-colors"
                    >
                      <div className="text-xs font-medium text-white/90 truncate">
                        {r.title}
                      </div>
                      <div className="text-[10px] text-white/40 mt-1">
                        {r.agent} · {r.tokens} tok · CAPO {r.capo}
                      </div>
                    </Link>
                  ))}
                  {items.length === 0 && (
                    <p className="text-[10px] text-white/20 text-center py-4">
                      -
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </DataCard>
    </main>
  );
}
