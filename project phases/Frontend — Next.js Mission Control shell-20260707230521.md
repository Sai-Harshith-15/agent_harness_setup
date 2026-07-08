# Frontend — Next.js Mission Control shell

# Next.js Mission Control shell (`frontend/`)
A minimal but runnable App-Router shell that boots against the Context Server's `GET /health` and renders live system state. Later phases add `/kanban`, `/tokens`, `/task/[id]`, `/hitl`, `/crash`, `/agents`, `/vault`.

* * *
## `frontend/package.json`

```json
{
  "name": "mission-control",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "@tanstack/react-query": "5.51.1"
  },
  "devDependencies": {
    "typescript": "5.5.3",
    "@types/react": "18.3.3",
    "@types/node": "20.14.10"
  }
}
```

* * *
## `frontend/next.config.js`

```plain
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    // Proxy /api/* to the Context Server so the browser avoids CORS + self-signed cert pain.
    return [
      { source: "/api/:path*", destination: "http://127.0.0.1:27180/:path*" },
    ];
  },
};
module.exports = nextConfig;
```

* * *
## `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
```

* * *
## `frontend/app/layout.tsx`

```plain
export const metadata = { title: "Mission Control" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "ui-sans-serif, system-ui", margin: 0, background: "#0b0f17", color: "#e6edf3" }}>
        {children}
      </body>
    </html>
  );
}
```

* * *
## `frontend/app/page.tsx`

```plain
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
  const color = ok ? "#3fb950" : health.status === "degraded" ? "#d29922" : "#f85149";

  return (
    <main style={{ maxWidth: 920, margin: "0 auto", padding: "48px 24px" }}>
      <h1 style={{ fontSize: 28 }}>Agentic OS — Mission Control</h1>
      <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 0" }}>
        <span style={{ width: 12, height: 12, borderRadius: 999, background: color }} />
        <strong style={{ textTransform: "uppercase", letterSpacing: 1 }}>{health.status}</strong>
        <span style={{ opacity: 0.7 }}>· Obsidian backend: {health.obsidian_backend ? "reachable" : "down"}</span>
      </div>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18, opacity: 0.9 }}>Active locks</h2>
        {state.locks.length === 0
          ? <p style={{ opacity: 0.6 }}>None held.</p>
          : <ul>{state.locks.map((l: any) => <li key={l.resource}>{l.resource} — {l.agent}:{l.task_id}</li>)}</ul>}
      </section>

      <section style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18, opacity: 0.9 }}>Recent activity</h2>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", opacity: 0.6 }}>
              <th style={{ padding: "6px 8px" }}>ts</th><th>agent</th><th>tool</th><th>ok</th><th>detail</th>
            </tr>
          </thead>
          <tbody>
            {state.recent_activity.map((a: any) => (
              <tr key={a.id} style={{ borderTop: "1px solid #21262d" }}>
                <td style={{ padding: "6px 8px", whiteSpace: "nowrap" }}>{a.ts}</td>
                <td>{a.agent}</td><td>{a.tool}</td>
                <td style={{ color: a.ok ? "#3fb950" : "#f85149" }}>{a.ok ? "✓" : "✕"}</td>
                <td style={{ opacity: 0.8 }}>{a.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
```

* * *
## `frontend/next-env.d.ts`

```plain
/// <reference types="next" />
/// <reference types="next/image-types/global" />
```

* * *
That's the full runnable backbone. Boot the backend, boot the frontend, and [http://127.0.0.1:3000](http://127.0.0.1:3000) will light up green once Obsidian + the Context Server are both live. Every `# TODO(phase-N)` marks where the next tasks in 901615745748 ([https://app.clickup.com/90161687318/v/li/901615745748](https://app.clickup.com/90161687318/v/li/901615745748)) plug in.