import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader } from "@/app/components/PageHeader";
import { DataCard } from "@/app/components/DataCard";

export default async function Agents() {
  const data = await api<any>("/dashboard/agents");

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto">
      <PageHeader
        title="Agents"
        description={`Orchestrator: ${data.orchestrator}`}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.agents.map((a: any) => (
          <Link
            key={a.id}
            href={`/task/${a.id}`}
            className="glass-panel p-5 hover:bg-white/[0.06] transition-colors group"
          >
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-bold text-white group-hover:text-accent transition-colors">
                {a.id}
              </h3>
              {a.role === "orchestrator" && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-accent/20 text-accent font-bold">
                  ORCH
                </span>
              )}
            </div>
            <div className="text-xs text-white/50 space-y-1">
              <div>
                Role: <span className="text-white/70">{a.role}</span>
              </div>
              <div>
                Adapter:{" "}
                <span className="text-white/70">{a.adapter || "http"}</span>
              </div>
              {(a.capabilities || []).length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {(a.capabilities || []).map((cap: string) => (
                    <span
                      key={cap}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/60"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
