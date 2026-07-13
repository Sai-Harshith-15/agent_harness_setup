import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import Home from "../app/page";

global.fetch = vi.fn((url) => {
  const urlStr = typeof url === "string" ? url : "";
  if (urlStr.includes("/health")) {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ status: "ok", obsidian_backend: true }),
    });
  }
  if (urlStr.includes("/dashboard/state")) {
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          locks: [],
          recent_activity: [],
          stalls: [],
        }),
    });
  }
  return Promise.reject(new Error("not found"));
}) as any;

describe("Mission Control Home", () => {
  it("renders without crashing and shows health status", async () => {
    const PageComponent = await Home();
    render(PageComponent);
    expect(
      screen.getByText("Agentic OS — Mission Control")
    ).toBeDefined();
    expect(screen.getByText(/reachable/i)).toBeDefined();
  });
});
