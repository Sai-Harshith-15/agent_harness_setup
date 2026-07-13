import { api } from "@/lib/api";
import {
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Play,
  Pause,
} from "lucide-react";
import { PageHeader } from "@/app/components/PageHeader";

interface Span {
  id: number;
  ts: string;
  agent: string;
  tool: string;
  ok: number;
  detail: string;
}

interface HitlItem {
  id: number;
  status: string;
  resolution: string;
  ts: string;
}

interface CrashItem {
  reason: string;
  frozen_state: string;
  created_at: string;
}

interface TokenItem {
  agent: string;
  tokens_in: number;
  tokens_out: number;
  model: string;
  cost_usd: number;
}

interface TaskData {
  task_id: string;
  spans: Span[];
  hitl: HitlItem[];
  crashes: CrashItem[];
  tokens: TokenItem[];
}

function computeStatus(task: TaskData): {
  label: string;
  icon: JSX.Element;
  color: string;
} {
  const hasCrash = task.crashes && task.crashes.length > 0;
  const openHitl =
    task.hitl &&
    task.hitl.some((h) => h.status === "open");
  const hasSpans = task.spans && task.spans.length > 0;
  const lastSpanOk =
    hasSpans && task.spans[task.spans.length - 1].ok === 1;

  if (hasCrash)
    return {
      label: "Crashed",
      icon: <AlertTriangle className="w-4 h-4" />,
      color: "border-danger/30 bg-danger/10",
    };
  if (openHitl)
    return {
      label: "Awaiting HITL",
      icon: <Pause className="w-4 h-4" />,
      color: "border-warning/30 bg-warning/10",
    };
  if (lastSpanOk)
    return {
      label: "Accepted",
      icon: <CheckCircle className="w-4 h-4" />,
      color: "border-success/30 bg-success/10",
    };
  return {
    label: "Active",
    icon: <Play className="w-4 h-4" />,
    color: "border-accent/30 bg-accent/10",
  };
}

const LIFECYCLE_STAGES = [
  "delegate",
  "research",
  "implement",
  "review",
  "accept",
];

export default async function Task({ params }: { params: { id: string } }) {
  let task: TaskData;
  try {
    task = await api<TaskData>(`/dashboard/task/${params.id}`);
  } catch {
    return (
      <main className="p-8 md:p-12 max-w-7xl mx-auto">
        <div className="glass-panel p-8 text-center">
          <AlertTriangle className="w-16 h-16 text-warning/40 mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">
            Task Not Found
          </h1>
          <p className="text-white/40 text-sm">
            Unable to load task &quot;{params.id}&quot;.
          </p>
        </div>
      </main>
    );
  }

  const status = computeStatus(task);
  const totalTokens = (task.tokens || []).reduce(
    (sum, t) => sum + (t.tokens_in || 0) + (t.tokens_out || 0),
    0
  );

  return (
    <main className="p-8 md:p-12 max-w-7xl mx-auto space-y-8">
      <PageHeader
        title={`Task: ${task.task_id}`}
        description="Audit trail and lifecycle"
      />

      <div
        className={`glass-panel p-4 border ${status.color} flex items-center gap-3`}
      >
        {status.icon}
        <span className="text-sm font-bold text-white">{status.label}</span>
        <span className="text-xs text-white/30 ml-auto font-mono">
          {task.task_id}
        </span>
      </div>

      <div className="flex items-center gap-1">
        {LIFECYCLE_STAGES.map((stage, i) => {
          const matched = task.spans?.some(
            (s) => s.tool === stage || s.tool.includes(stage)
          );
          return (
            <div
              key={stage}
              className={`flex-1 h-1.5 rounded-full ${
                matched ? "bg-accent" : "bg-white/10"
              }`}
              title={stage}
            />
          );
        })}
      </div>

      <section>
        <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold mb-3 flex items-center gap-2">
          <Clock className="w-4 h-4" /> Timeline
        </h2>
        <div className="glass-panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-white/40 uppercase text-[11px] tracking-wider border-b border-white/5">
                  <th className="py-2 px-4 font-medium">Time</th>
                  <th className="py-2 px-4 font-medium">Agent</th>
                  <th className="py-2 px-4 font-medium">Tool</th>
                  <th className="py-2 px-4 font-medium">Status</th>
                  <th className="py-2 px-4 font-medium">Detail</th>
                </tr>
              </thead>
              <tbody>
                {(task.spans || []).map((s) => (
                  <tr
                    key={s.id}
                    className="border-t border-white/5 hover:bg-white/[0.02]"
                  >
                    <td className="py-2 px-4 font-mono text-xs text-white/50">
                      {s.ts}
                    </td>
                    <td className="py-2 px-4 text-white/80 font-medium">
                      {s.agent}
                    </td>
                    <td className="py-2 px-4 font-mono text-xs text-accent">
                      {s.tool}
                    </td>
                    <td className="py-2 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                          s.ok
                            ? "bg-success/20 text-success"
                            : "bg-danger/20 text-danger"
                        }`}
                      >
                        {s.ok ? "OK" : "FAIL"}
                      </span>
                    </td>
                    <td className="py-2 px-4 text-xs text-white/40 max-w-[200px] truncate">
                      {s.detail || "-"}
                    </td>
                  </tr>
                ))}
                {(task.spans || []).length === 0 && (
                  <tr>
                    <td
                      colSpan={5}
                      className="py-8 text-center text-sm text-white/30"
                    >
                      No timeline events recorded.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {task.hitl && task.hitl.length > 0 && (
        <section>
          <h2 className="text-sm uppercase tracking-widest text-warning font-semibold mb-3">
            HITL Interactions
          </h2>
          <div className="space-y-2">
            {task.hitl.map((h) => (
              <div
                key={h.id}
                className="glass-panel p-3 border border-warning/20 text-sm"
              >
                <span className="text-white/70">
                  Status: {h.status}
                </span>
                {h.resolution && (
                  <span className="text-white/40 ml-3">
                    Resolution: {h.resolution}
                  </span>
                )}
                <span className="text-white/30 ml-3 text-xs">
                  {h.ts}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section>
        <h2 className="text-sm uppercase tracking-widest text-white/40 font-semibold mb-3">
          Token Ledger ({totalTokens.toLocaleString()} total)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {(task.tokens || []).map((t, i) => (
            <div key={i} className="glass-panel p-3">
              <div className="text-xs text-accent font-mono mb-1">
                {t.agent}
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-white/50">In: {t.tokens_in || 0}</span>
                <span className="text-white/50">
                  Out: {t.tokens_out || 0}
                </span>
              </div>
              <div className="text-[10px] text-white/30 mt-1">
                {t.model || "unknown"} · $
                {(t.cost_usd || 0).toFixed(4)}
              </div>
            </div>
          ))}
          {(task.tokens || []).length === 0 && (
            <p className="text-sm text-white/30 col-span-full text-center py-4">
              No token records.
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
