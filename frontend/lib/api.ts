const BASE = typeof window === "undefined" ? "http://127.0.0.1:27180" : "/api";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", ...init });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const AGENT_HEADER = { "X-Agent-Identity": "mission-control:ui" };
