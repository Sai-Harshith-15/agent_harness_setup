"use client";
export default function Error({ error, reset }: { error: Error & { digest?: string }, reset: () => void }) {
  return (
    <div style={{ padding: 24, color: "#ff7b72" }}>
      <h2>Backend Error</h2>
      <p style={{ fontFamily: "monospace", marginTop: 12 }}>{error.message}</p>
      <button onClick={() => reset()} style={{ marginTop: 24, cursor: "pointer", background: "#21262d", padding: "8px 16px", borderRadius: 6 }}>Try again</button>
    </div>
  );
}
