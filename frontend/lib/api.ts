const BACKEND = process.env.NEXT_PUBLIC_CONTEXT_SERVER || "http://127.0.0.1:27180";
const PROXY = "/api";

function baseUrl(): string {
  return typeof window === "undefined" ? BACKEND : PROXY;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${baseUrl()}${path}`;
  const res = await fetch(url, { cache: "no-store", ...init });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${path} -> ${res.status}: ${detail}`);
  }
  return res.json();
}

export function getAgentHeaders(): Record<string, string> {
  return { "X-Agent-Identity": "mission-control:ui:dashboard" };
}
