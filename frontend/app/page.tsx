import { Activity, Lock, Cpu, Server, ShieldCheck, ShieldAlert, AlertCircle } from "lucide-react";
import { ActivityStream } from "./components/ActivityStream";

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
  const degraded = health.status === "degraded";
  
  const statusColor = ok ? "bg-success" : degraded ? "bg-warning" : "bg-danger";

  return (
    <main className="p-8 md:p-12 lg:p-16 max-w-7xl mx-auto space-y-12">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-2">Agentic OS — Mission Control</h1>
          <p className="text-white/50 text-lg">Real-time metrics and agent activity.</p>
        </div>
        
        <div className="glass-panel px-6 py-4 flex items-center gap-4 border border-white/5">
          <div className="relative flex items-center justify-center h-5 w-5">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${statusColor}`}></span>
            <span className={`relative inline-flex rounded-full h-3 w-3 ${statusColor}`}></span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="uppercase tracking-widest text-xs font-bold text-white/80">{health.status}</span>
            </div>
            <div className="text-[10px] text-white/40 uppercase tracking-wider mt-0.5">
              <span className={health.obsidian_backend ? "text-success/80" : "text-danger/80"}>
                Obsidian backend: {health.obsidian_backend ? "reachable" : "down"}
              </span>
            </div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Locks & Quick Stats */}
        <div className="lg:col-span-1 space-y-8">
          <section className="glass-panel flex flex-col h-full min-h-[300px]">
            <div className="p-6 border-b border-white/5 bg-white/[0.02]">
              <div className="flex items-center justify-between">
                <h2 className="text-sm uppercase tracking-widest text-white/50 font-semibold flex items-center gap-2">
                  <Lock className="w-4 h-4" /> Active Locks
                </h2>
                <span className="bg-white/10 text-white/80 text-xs py-1 px-2 rounded-full font-mono">
                  {state.locks.length}
                </span>
              </div>
            </div>
            
            <div className="p-6 flex-1 flex flex-col">
              {state.locks.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center py-12 text-center">
                  <ShieldCheck className="w-12 h-12 mb-4 text-white/10" />
                  <p className="text-sm text-white/40">No resources currently locked.</p>
                </div>
              ) : (
                <ul className="space-y-3 flex-1">
                  {state.locks.map((l: any) => (
                    <li key={l.resource} className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col gap-2 transition-colors hover:bg-white/10">
                      <span className="font-mono text-xs text-accent">{l.resource}</span>
                      <span className="text-sm text-white/60">
                        {l.agent} <span className="opacity-40">({l.task_id})</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>

        {/* Right Column: Activity Stream */}
        <div className="lg:col-span-2">
          <ActivityStream initialActivity={state.recent_activity} />
        </div>
        
      </div>
    </main>
  );
}
