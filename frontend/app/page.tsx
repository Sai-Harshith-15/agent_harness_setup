import { Activity, Lock, Server, ShieldCheck, ShieldAlert, Cpu } from "lucide-react";
import { ActivityStream } from "./components/ActivityStream";
import { StatusBadge } from "./components/StatusBadge";

const BACKEND =
  process.env.NEXT_PUBLIC_CONTEXT_SERVER || "http://127.0.0.1:27180";

async function getHealth() {
  try {
    const res = await fetch(`${BACKEND}/health`, { cache: "no-store" });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function getState() {
  try {
    const res = await fetch(`${BACKEND}/dashboard/state`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export default async function Home() {
  const health = await getHealth();
  const state = await getState();

  if (!health || !state) {
    return (
      <main className="p-8 md:p-12 lg:p-16 max-w-7xl mx-auto min-h-screen">
        <div className="glass-panel p-8 text-center space-y-4">
          <Server className="w-16 h-16 text-danger/40 mx-auto" />
          <h1 className="text-2xl font-bold text-white">
            Context Server Unreachable
          </h1>
          <p className="text-white/40 text-sm">
            The context server at {BACKEND} is not responding.
            <br />
            Please ensure it is running on port 27180.
          </p>
        </div>
      </main>
    );
  }

  const ok = health.status === "ok";
  const degraded = health.status === "degraded";

  return (
    <main className="p-8 md:p-12 lg:p-16 max-w-7xl mx-auto space-y-12">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white mb-2">
            Agentic OS — Mission Control
          </h1>
          <p className="text-white/50 text-lg">
            Real-time metrics and agent activity.
          </p>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <StatusBadge
            status={health.status}
            ok={ok}
            degraded={degraded}
          />
          <div className="text-[10px] text-white/40 uppercase tracking-wider">
            Obsidian:{" "}
            <span
              className={
                health.obsidian_backend ? "text-success/80" : "text-danger/80"
              }
            >
              {health.obsidian_backend ? "reachable" : "down"}
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
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
                  <p className="text-sm text-white/40">
                    No resources currently locked.
                  </p>
                </div>
              ) : (
                <ul className="space-y-3 flex-1">
                  {state.locks.map((l: any) => (
                    <li
                      key={l.resource}
                      className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col gap-2 transition-colors hover:bg-white/10"
                    >
                      <span className="font-mono text-xs text-accent">
                        {l.resource}
                      </span>
                      <span className="text-sm text-white/60">
                        {l.agent}{" "}
                        <span className="opacity-40">({l.task_id})</span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>

        <div className="lg:col-span-2">
          <ActivityStream initialActivity={state.recent_activity} />
        </div>
      </div>

      {state.stalls && state.stalls.length > 0 && (
        <section className="glass-panel p-6 border border-warning/30">
          <h2 className="text-sm uppercase tracking-widest text-warning font-semibold flex items-center gap-2 mb-4">
            <ShieldAlert className="w-4 h-4" /> Stalled Tasks
          </h2>
          <div className="space-y-2">
            {state.stalls.map((s: any) => (
              <div
                key={s.id}
                className="text-sm text-white/60 bg-white/5 rounded-lg p-3"
              >
                <span className="text-accent font-mono text-xs">
                  {s.task_id}
                </span>
                <span className="ml-3">{s.question || s.reason}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
