import { api } from "@/lib/api";
import { Clock, AlertTriangle, CheckCircle, Database, GitBranch, Play, Pause, XCircle, ArrowRight } from "lucide-react";

interface Span {
  id: number;
  ts: string;
  agent: string;
  tool: string;
  ok: boolean;
  detail: string;
}

interface HitlItem {
  id: number;
  status: string;
  ts: string;
  resolution?: string;
}

interface TokenItem {
  agent: string;
  model: string;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
}

interface CrashItem {
  reason: string;
  created_at: string;
  frozen_state?: string;
}

interface TaskData {
  task_id: string;
  spans: Span[];
  hitl: HitlItem[];
  tokens: TokenItem[];
  crashes: CrashItem[];
}

function computeStatus(task: TaskData): { label: string; icon: JSX.Element; color: string } {
  if (task.crashes.length > 0) {
    const latest = task.crashes[task.crashes.length - 1];
    if (latest.reason.toLowerCase().includes("hibernat")) {
      return { label: "Hibernated", icon: <Pause size={16} />, color: "#d29922" };
    }
    return { label: "Crashed", icon: <XCircle size={16} />, color: "#f85149" };
  }
  const acceptedSpan = task.spans.find(s => s.detail.includes("accepted"));
  if (acceptedSpan) {
    return { label: "Accepted", icon: <CheckCircle size={16} />, color: "#3fb950" };
  }
  const hitlOpen = task.hitl.some(h => h.status === "open" || h.status === "pending");
  if (hitlOpen) {
    return { label: "Awaiting HITL", icon: <AlertTriangle size={16} />, color: "#d29922" };
  }
  if (task.spans.length > 0) {
    const lastSpan = task.spans[task.spans.length - 1];
    if (!lastSpan.ok) {
      return { label: "Last span failed", icon: <AlertTriangle size={16} />, color: "#f85149" };
    }
    return { label: "Active", icon: <Play size={16} />, color: "#58a6ff" };
  }
  return { label: "Unknown", icon: <AlertTriangle size={16} />, color: "#8b949e" };
}

interface TimelineEvent {
  type: "span" | "delegation" | "hitl" | "crash" | "hibernation";
  ts: string;
  content: JSX.Element;
}

function buildTimeline(task: TaskData): TimelineEvent[] {
  const events: TimelineEvent[] = [];

  for (const s of task.spans) {
    const isDelegation = s.tool === "delegate_task";
    events.push({
      type: isDelegation ? "delegation" : "span",
      ts: s.ts,
      content: (
        <div style={{ display: "flex", alignItems: "start", gap: 10 }}>
          {isDelegation ? (
            <GitBranch size={14} color="#a371f7" style={{ marginTop: 2, flexShrink: 0 }} />
          ) : s.ok ? (
            <CheckCircle size={14} color="#3fb950" style={{ marginTop: 2, flexShrink: 0 }} />
          ) : (
            <XCircle size={14} color="#f85149" style={{ marginTop: 2, flexShrink: 0 }} />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: isDelegation ? "#a371f7" : s.ok ? "#c9d1d9" : "#f85149" }}>
              {isDelegation ? "↳ Delegated to " : `[${s.agent}] `}
              {isDelegation ? s.detail.replace(/^->\s*/, "") : s.tool}
              {!isDelegation && (s.ok ? " ✓" : " ✕")}
            </div>
            {s.detail && !isDelegation && (
              <div style={{ color: "#8b949e", fontSize: 13, marginTop: 2 }}>{s.detail}</div>
            )}
          </div>
        </div>
      ),
    });
  }

  for (const h of task.hitl) {
    events.push({
      type: "hitl",
      ts: h.ts,
      content: (
        <div style={{ display: "flex", alignItems: "start", gap: 10 }}>
          <AlertTriangle size={14} color="#d29922" style={{ marginTop: 2, flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: "#d29922" }}>HITL Review — {h.status}</div>
            {h.resolution && (
              <div style={{ color: "#8b949e", fontSize: 13, marginTop: 2, fontStyle: "italic" }}>
                Resolution: {h.resolution}
              </div>
            )}
          </div>
        </div>
      ),
    });
  }

  for (const c of task.crashes) {
    const isHibernation = c.reason.toLowerCase().includes("hibernat");
    events.push({
      type: isHibernation ? "hibernation" : "crash",
      ts: c.created_at,
      content: (
        <div style={{ display: "flex", alignItems: "start", gap: 10 }}>
          {isHibernation ? (
            <Pause size={14} color="#d29922" style={{ marginTop: 2, flexShrink: 0 }} />
          ) : (
            <XCircle size={14} color="#f85149" style={{ marginTop: 2, flexShrink: 0 }} />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600, color: isHibernation ? "#d29922" : "#f85149" }}>
              {isHibernation ? "Hibernated" : "Crashed"}: {c.reason}
            </div>
          </div>
        </div>
      ),
    });
  }

  events.sort((a, b) => a.ts.localeCompare(b.ts));
  return events;
}

export default async function Task({ params }: { params: { id: string } }) {
  const task: TaskData = await api<TaskData>(`/dashboard/task/${params.id}`);
  if (!task) return <div style={{ padding: 24, color: "#f85149" }}>Failed to load task.</div>;

  const status = computeStatus(task);
  const timeline = buildTimeline(task);
  const totalCost = task.tokens.reduce((sum, t) => sum + (t.cost_usd || 0), 0);
  const totalTokens = task.tokens.reduce((sum, t) => sum + (t.input_tokens || 0) + (t.output_tokens || 0), 0);

  return (
    <main style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      {/* Status Banner */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16, padding: "16px 20px",
        background: "#0d1117", border: "1px solid #30363d", borderRadius: 8,
        marginBottom: 24
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: "50%", display: "flex",
          alignItems: "center", justifyContent: "center",
          background: `${status.color}22`, border: `2px solid ${status.color}`
        }}>
          {status.icon}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#c9d1d9" }}>Task {params.id}</div>
          <div style={{ fontSize: 14, color: status.color, fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
            {status.label}
            {task.spans.length > 0 && (
              <span style={{ color: "#8b949e", fontWeight: 400 }}>
                · {task.spans.length} span{task.spans.length !== 1 ? "s" : ""}
              </span>
            )}
            {totalCost > 0 && (
              <span style={{ color: "#3fb950", fontWeight: 400 }}>
                · ${totalCost.toFixed(4)}
              </span>
            )}
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 12, color: "#8b949e" }}>
            {totalTokens.toLocaleString()} tokens
          </div>
          <div style={{ fontSize: 12, color: "#8b949e" }}>
            {timeline.length} events
          </div>
        </div>
      </div>

      {/* Lifecycle Progress Bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 0, marginBottom: 32,
        background: "#161b22", borderRadius: 8, padding: "8px 16px",
        border: "1px solid #30363d"
      }}>
        {[
          { label: "Delegation", icon: <GitBranch size={12} />, active: task.spans.some(s => s.tool === "delegate_task") },
          { label: "Execution", icon: <Play size={12} />, active: task.spans.length > 0 },
          { label: "HITL", icon: <AlertTriangle size={12} />, active: task.hitl.length > 0 },
          { label: "Crash", icon: <XCircle size={12} />, active: task.crashes.length > 0 },
          { label: "Accepted", icon: <CheckCircle size={12} />, active: status.label === "Accepted" },
        ].map((stage, i, arr) => (
          <div key={stage.label} style={{ display: "flex", alignItems: "center", flex: 1 }}>
            <div style={{
              display: "flex", alignItems: "center", gap: 4,
              color: stage.active ? stage.label === "Accepted" ? "#3fb950" : stage.label === "Crash" ? "#f85149" : "#c9d1d9" : "#484f58",
              fontSize: 12, fontWeight: 500
            }}>
              {stage.icon} {stage.label}
            </div>
            {i < arr.length - 1 && (
              <div style={{ flex: 1, height: 2, background: stage.active ? "#30363d" : "#21262d", margin: "0 8px" }} />
            )}
          </div>
        ))}
      </div>

      {/* Integrated Timeline */}
      <section>
        <h2 style={{
          fontSize: 18, display: "flex", alignItems: "center", gap: 8,
          borderBottom: "1px solid #30363d", paddingBottom: 10, marginBottom: 16
        }}>
          <Clock size={18} /> Integrated Timeline
        </h2>
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 4 }}>
          {timeline.map((event, i) => {
            const typeColors: Record<string, string> = {
              span: "#30363d",
              delegation: "#a371f722",
              hitl: "#d2992222",
              crash: "#f8514922",
              hibernation: "#d2992222",
            };
            return (
              <div key={i} style={{
                display: "flex", alignItems: "start", gap: 14, padding: "10px 14px",
                borderBottom: i < timeline.length - 1 ? "1px solid #21262d" : "none",
                background: typeColors[event.type] || "transparent",
                borderRadius: 4,
              }}>
                <span style={{
                  color: "#8b949e", fontFamily: "monospace", fontSize: 11,
                  marginTop: 2, minWidth: 60, flexShrink: 0
                }}>
                  {event.ts.includes("T") ? event.ts.split("T")[1]?.slice(0, 8) : event.ts.split(" ")[1] || event.ts}
                </span>
                <div style={{ flex: 1 }}>{event.content}</div>
              </div>
            );
          })}
          {timeline.length === 0 && (
            <div style={{ padding: 20, color: "#8b949e", textAlign: "center" }}>
              No events recorded for this task.
            </div>
          )}
        </div>
      </section>

      {/* Token Ledger Summary */}
      <section style={{ marginTop: 32 }}>
        <h2 style={{
          fontSize: 18, display: "flex", alignItems: "center", gap: 8,
          borderBottom: "1px solid #30363d", paddingBottom: 10, marginBottom: 16
        }}>
          <Database size={18} /> Token Ledger {totalCost > 0 && (
            <span style={{ fontSize: 14, color: "#3fb950", fontWeight: 400 }}>
              — ${totalCost.toFixed(4)} total
            </span>
          )}
        </h2>
        <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: 16 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 8 }}>
            {task.tokens.map((t, i) => (
              <div key={i} style={{
                background: "#161b22", borderRadius: 6, padding: 12,
                border: "1px solid #21262d"
              }}>
                <div style={{ fontWeight: 600, color: "#c9d1d9", marginBottom: 4 }}>
                  {t.agent}
                  <span style={{ color: "#8b949e", fontWeight: 400, fontSize: 13, marginLeft: 8 }}>
                    {t.model}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                  <span style={{ color: "#8b949e" }}>
                    {t.input_tokens.toLocaleString()} in / {t.output_tokens.toLocaleString()} out
                  </span>
                  <span style={{ color: "#3fb950", fontWeight: 600 }}>
                    ${t.cost_usd.toFixed(4)}
                  </span>
                </div>
              </div>
            ))}
          </div>
          {task.tokens.length === 0 && (
            <div style={{ color: "#8b949e" }}>No token spend recorded.</div>
          )}
        </div>
      </section>
    </main>
  );
}
