# Phase 9 — Next.js Mission Control (full pages)

# Phase 9 — Next.js Mission Control (full pages)
Brings the frontend home: the Jira-style Kanban parsing `PLAN.md`, the `/tokens` analytics page, `/task/[id]` trajectory, the `/hitl` diff-modal + clarification queue, `/crash`, `/agents`, and `/vault`. Everything reads the `/dashboard/*` surfaces Phases 2–8 already expose — no second API. Copy each file into `D:\GitRepo\agent_harness_setup\frontend\` at the path in its heading.
> Depends on Phases 0–8. Builds on the Phase 0–2 shell (`app/layout.tsx`, `app/page.tsx`). All fetches hit the Context Server on `:27180` (the `next.config.js` rewrite proxies `/api/*`).
* * *
## `frontend/lib/api.ts` — one tiny fetch helper

```plain
const BASE = "http://127.0.0.1:27180";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const AGENT_HEADER = { "X-Agent-Identity": "mission-control:ui" };
```

* * *
## `frontend/app/nav.tsx` — shared top nav

```plain
import Link from "next/link";

const LINKS = [
  ["/", "Mission Control"], ["/kanban", "Kanban"], ["/tokens", "Tokens"],
  ["/hitl", "HITL"], ["/crash", "Crash"], ["/agents", "Agents"], ["/vault", "Vault"],
];

export default function Nav() {
  return (
    <nav style={{ display: "flex", gap: 16, padding: "12px 24px", borderBottom: "1px solid #21262d" }}>
      {LINKS.map(([href, label]) => (
        <Link key={href} href={href} style={{ color: "#58a6ff", textDecoration: "none" }}>{label}</Link>
      ))}
    </nav>
  );
}
```

> Drop `<Nav />` at the top of `app/layout.tsx`'s `<body>` so every page has it.
* * *
## `frontend/app/kanban/page.tsx` — Jira-style board from [PLAN.md](http://PLAN.md)

```plain
import { api } from "@/lib/api";

type Row = { status: string; id: string; title: string; agent: string; capo: number; tokens: number };
const COLUMNS = ["backlog", "in-progress", "delegated", "awaiting-hitl", "hibernated", "done", "rejected"];

async function getPlan(): Promise<Row[]> {
  try { return (await api<{ rows: Row[] }>("/dashboard/plan")).rows; } catch { return []; }
}

export default async function Kanban() {
  const rows = await getPlan();
  return (
    <main style={{ padding: 24 }}>
      <h1>Kanban</h1>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${COLUMNS.length}, 1fr)`, gap: 12 }}>
        {COLUMNS.map((col) => (
          <div key={col} style={{ background: "#0d1117", borderRadius: 8, padding: 8, minHeight: 200 }}>
            <h3 style={{ fontSize: 12, textTransform: "uppercase", opacity: 0.6 }}>{col}</h3>
            {rows.filter((r) => r.status === col).map((r) => (
              <a key={r.id} href={`/task/${r.id}`} style={{ display: "block", background: "#161b22",
                   border: "1px solid #21262d", borderRadius: 6, padding: 8, margin: "8px 0", color: "#e6edf3", textDecoration: "none" }}>
                <div style={{ fontSize: 13 }}>{r.title}</div>
                <div style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>
                  {r.agent} · {r.tokens} tok · CAPO {r.capo}
                </div>
              </a>
            ))}
          </div>
        ))}
      </div>
    </main>
  );
}
```

* * *
## Add the [PLAN.md](http://PLAN.md) parser to the backend: `/dashboard/plan`

```python
# context_server/app/main.py
import re, os

_PLAN_ROW = re.compile(
    r"- \[(?P<status>[^\]]+)\] \((?P<id>[^)]+)\) (?P<title>.+?) \| agent=(?P<agent>\S+)"
    r"(?: capo=(?P<capo>\d+))?(?: tokens=(?P<tokens>\d+))?"
)

@app.get("/dashboard/plan")
async def dashboard_plan():
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "PLAN.md")
    rows = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = _PLAN_ROW.match(line.strip())
            if m:
                d = m.groupdict()
                rows.append({"status": d["status"], "id": d["id"], "title": d["title"],
                             "agent": d["agent"], "capo": int(d["capo"] or 0), "tokens": int(d["tokens"] or 0)})
    return {"rows": rows}
```

* * *
## `frontend/app/tokens/page.tsx` — analytics

```plain
import { api } from "@/lib/api";

export default async function Tokens() {
  const [tok, capo] = await Promise.all([
    api<any>("/dashboard/tokens").catch(() => ({ by_task: [], heatmap: [] })),
    api<any>("/dashboard/capo").catch(() => ({ summary: {}, trend: [] })),
  ]);
  return (
    <main style={{ padding: 24 }}>
      <h1>Token analytics</h1>
      <p>CAPO: <strong>{capo.summary?.capo ?? "n/a"}</strong> tokens/accepted
         ({capo.summary?.accepted_tasks ?? 0} accepted, {capo.summary?.total_tokens ?? 0} total)</p>

      <h2 style={{ fontSize: 16 }}>Top tasks by spend</h2>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
        <thead><tr style={{ textAlign: "left", opacity: 0.6 }}><th>task</th><th>tokens</th><th>accepted</th></tr></thead>
        <tbody>
          {tok.by_task.map((t: any) => (
            <tr key={t.task_id} style={{ borderTop: "1px solid #21262d" }}>
              <td style={{ padding: "6px 8px" }}><a href={`/task/${t.task_id}`} style={{ color: "#58a6ff" }}>{t.task_id}</a></td>
              <td>{t.total_tokens}</td><td>{t.accepted ? "✓" : "…"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ fontSize: 16, marginTop: 24 }}>Agent × tool heatmap</h2><ul>{tok.heatmap.map((h: any, i: number) => <li key={i}>{h.agent} · {h.tool}: {h.tokens} tok</li>)}</ul>
    </main>
  );
}
```

* * *
## `frontend/app/task/[id]/page.tsx` — trajectory view

```plain
import { api } from "@/lib/api";

export default async function Task({ params }: { params: { id: string } }) {
  const state = await api<any>("/dashboard/state").catch(() => ({ recent_activity: [] }));
  const spans = state.recent_activity.filter((a: any) => a.task_id === params.id);
  return (
    <main style={{ padding: 24 }}>
      <h1>Task {params.id}</h1>
      <h2 style={{ fontSize: 16 }}>Trajectory</h2><ol>
        {spans.map((s: any) => (
          <li key={s.id} style={{ margin: "6px 0", color: s.ok ? "#e6edf3" : "#f85149" }}>
            <code>{s.ts}</code> · {s.agent} · <strong>{s.tool}</strong> {s.ok ? "✓" : "✕"} — {s.detail}
          </li>
        ))}
        {spans.length === 0 && <p style={{ opacity: 0.6 }}>No spans recorded for this task.</p>}
      </ol>
    </main>
  );
}
```

* * *
## `frontend/app/hitl/page.tsx` — clarification queue + diff-modal (client component)

```plain
"use client";
import { useEffect, useState } from "react";

export default function Hitl() {
  const [items, setItems] = useState<any[]>([]);
  const [active, setActive] = useState<any | null>(null);

  const load = () => fetch("http://127.0.0.1:27180/dashboard/hitl")
    .then((r) => r.json()).then((d) => setItems(d.open || [])).catch(() => setItems([]));
  useEffect(() => { load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);

  async function resolve(status: string) {
    await fetch("http://127.0.0.1:27180/dashboard/hitl", {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_id: active.id, status, resolution: status }),
    });
    setActive(null); load();
  }

  return (
    <main style={{ padding: 24 }}>
      <h1>HITL queue</h1>
      {items.length === 0 && <p style={{ opacity: 0.6 }}>Nothing awaiting a human.</p>}
      {items.map((it) => (
        <div key={it.id} style={{ border: "1px solid #21262d", borderRadius: 8, padding: 12, margin: "8px 0" }}>
          <div><strong>{it.agent}</strong> · task {it.task_id}</div>
          <div style={{ margin: "6px 0" }}>{it.question}</div>
          <button onClick={() => setActive(it)} style={{ cursor: "pointer" }}>Review diff</button>
        </div>
      ))}

      {active && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", display: "grid", placeItems: "center" }}>
          <div style={{ background: "#0d1117", border: "1px solid #30363d", borderRadius: 10, padding: 20, width: 560 }}>
            <h3>Proposed change</h3>
            <pre style={{ background: "#161b22", padding: 12, borderRadius: 6, overflow: "auto", fontSize: 12 }}>
{JSON.stringify(active.proposed_diff ? JSON.parse(active.proposed_diff) : {}, null, 2)}
            </pre>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button onClick={() => resolve("approved")}>Approve</button>
              <button onClick={() => resolve("modified")}>Modify</button>
              <button onClick={() => resolve("rejected")}>Reject</button>
              <button onClick={() => setActive(null)} style={{ marginLeft: "auto" }}>Close</button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
```

* * *
## `frontend/app/crash/page.tsx` — crash-reconciliation feed

```plain
import { api } from "@/lib/api";

export default async function Crash() {
  const data = await api<any>("/dashboard/crashes").catch(() => ({ released_locks: [], hibernated_orphans: [] }));
  return (
    <main style={{ padding: 24 }}>
      <h1>Crash reconciliation</h1>
      <h2 style={{ fontSize: 16 }}>Released locks (crash_recovery)</h2><ul>{data.released_locks.map((l: any, i: number) => <li key={i}>{l.resource} — was {l.was}</li>)}</ul>
      {data.released_locks.length === 0 && <p style={{ opacity: 0.6 }}>No orphaned leases.</p>}
      <h2 style={{ fontSize: 16, marginTop: 16 }}>Hibernated orphans</h2><ul>{data.hibernated_orphans.map((o: any) => <li key={o.task_id}>{o.task_id} — {o.reason}</li>)}</ul>
    </main>
  );
}
```

* * *
## `frontend/app/agents/page.tsx` — registry browser

```plain
import { api } from "@/lib/api";

export default async function Agents() {
  const data = await api<any>("/dashboard/agents").catch(() => ({ agents: [], orchestrator: null }));
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
```

* * *
## `frontend/app/vault/page.tsx` — read-only Obsidian command center

```plain
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
```

* * *
## Smoke test (Definition of Done)

```bash
# Backend must expose the plan parser (added above)
curl http://127.0.0.1:27180/dashboard/plan     # -> {"rows": [...] from PLAN.md}

# Then, with frontend running (npm run dev):
#  /            -> live health + locks + activity   (Phase 0-2 shell)
#  /kanban      -> PLAN.md rows bucketed into 7 columns, tickets link to /task/[id]
#  /tokens      -> CAPO value + top-tasks table + agent×tool heatmap
#  /task/<id>   -> that task's span trajectory from the audit log
#  /hitl        -> open clarifications; 'Review diff' opens the modal; approve/modify/reject resolves + thaws
#  /crash       -> released crash_recovery locks + hibernated orphans
#  /agents      -> registry cards, orchestrator starred
#  /vault       -> browse vault root, click a note to read it (read-only)
```

Every page renders off a `/dashboard/*` surface the earlier phases already expose, so there's no second API and no new backend work beyond the `/dashboard/plan` parser. Kanban buckets real [PLAN.md](http://PLAN.md) rows, the HITL modal actually resolves and thaws the paused task, and /vault is strictly read-only. That's the Phase 9 Definition of Done — and the whole system, Phases 0–9, is now runnable end to end.

**You now have the full build in this doc.** Boot order: Obsidian (plugin on) → Context Server (`python -m app.main`) → `npm run dev`, then open [http://127.0.0.1:3000](http://127.0.0.1:3000). The remaining real-world seams are all flagged `TODO(phase-N)`: real agent runners (Phase 3), a real tokenizer + LLM summaries (Phase 5), OTel export, and signed identity tokens (Phase 2.8).