"use client";

import { create } from "zustand";

interface LogEntry {
  id: number;
  ts: string;
  agent: string;
  task_id: string;
  tool: string;
  ok: number;
  detail: string;
}

interface AppState {
  logs: LogEntry[];
  addLog: (log: LogEntry) => void;
  connectWebSockets: () => () => void;
}

let wsEvents: WebSocket | null = null;
let wsTokens: WebSocket | null = null;

function getWsBase(): string {
  const backend = process.env.NEXT_PUBLIC_CONTEXT_SERVER || "http://127.0.0.1:27180";
  return backend.replace(/^http/, "ws");
}

export const useStore = create<AppState>((set, get) => ({
  logs: [],
  addLog: (log) =>
    set((state) => ({ logs: [log, ...state.logs].slice(0, 100) })),
  connectWebSockets: () => {
    if (wsEvents && wsEvents.readyState === WebSocket.OPEN) wsEvents.close();
    if (wsTokens && wsTokens.readyState === WebSocket.OPEN) wsTokens.close();
    wsEvents = null;
    wsTokens = null;

    const base = getWsBase();

    const events = new WebSocket(`${base}/dashboard/events`);
    const tokens = new WebSocket(`${base}/dashboard/tokens/ws`);

    wsEvents = events;
    wsTokens = tokens;

    events.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "audit") {
          get().addLog({
            id: Date.now(),
            ts: new Date().toISOString(),
            agent: data.agent,
            task_id: data.task_id,
            tool: data.tool,
            ok: data.ok ? 1 : 0,
            detail: data.detail,
          });
        }
      } catch {
        // ignore parse errors
      }
    };
    events.onclose = () => {
      if (wsEvents === events) wsEvents = null;
    };
    events.onerror = () => {
      wsEvents = null;
    };

    tokens.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.by_task || data.capo) {
          // consume silently
        }
      } catch {
        // ignore
      }
    };
    tokens.onclose = () => {
      if (wsTokens === tokens) wsTokens = null;
    };
    tokens.onerror = () => {
      wsTokens = null;
    };

    return () => {
      if (events.readyState === WebSocket.OPEN) events.close();
      if (tokens.readyState === WebSocket.OPEN) tokens.close();
      if (wsEvents === events) wsEvents = null;
      if (wsTokens === tokens) wsTokens = null;
    };
  },
}));
