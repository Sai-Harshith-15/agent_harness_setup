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
    if (wsEvents) {
      return () => {
        wsEvents?.close();
        wsTokens?.close();
        wsEvents = null;
        wsTokens = null;
      };
    }

    const base = getWsBase();

    try {
      wsEvents = new WebSocket(`${base}/dashboard/events`);
      wsEvents.onmessage = (event) => {
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
      wsEvents.onclose = () => {
        wsEvents = null;
      };
    } catch {
      wsEvents = null;
    }

    try {
      wsTokens = new WebSocket(`${base}/dashboard/tokens/ws`);
      wsTokens.onmessage = (event) => {
        try {
          console.log("Token event:", JSON.parse(event.data));
        } catch {
          // ignore
        }
      };
      wsTokens.onclose = () => {
        wsTokens = null;
      };
    } catch {
      wsTokens = null;
    }

    return () => {
      wsEvents?.close();
      wsTokens?.close();
      wsEvents = null;
      wsTokens = null;
    };
  },
}));
