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
