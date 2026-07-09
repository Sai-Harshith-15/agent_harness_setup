"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Home, LayoutGrid, Palette, Terminal, AlertTriangle, Users, Database } from "lucide-react";

const LINKS = [
  { href: "/", label: "Mission Control", icon: Home },
  { href: "/kanban", label: "Kanban", icon: LayoutGrid },
  { href: "/tokens", label: "Tokens", icon: Palette },
  { href: "/hitl", label: "HITL", icon: Terminal },
  { href: "/crash", label: "Crash", icon: AlertTriangle },
  { href: "/agents", label: "Agents", icon: Users },
  { href: "/vault", label: "Vault", icon: Database },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-row md:flex-col gap-2 p-4 md:p-6 md:w-72 border-b md:border-b-0 md:border-r border-white/5 bg-white/[0.01] backdrop-blur-xl shrink-0 overflow-x-auto md:overflow-visible">
      <div className="hidden md:block mb-8 px-4 font-semibold tracking-[0.2em] text-xs uppercase text-white/30">
        Agentic OS
      </div>
      {LINKS.map(({ href, label, icon: Icon }) => {
        const isActive = pathname === href;
        return (
          <Link
            key={href}
            href={href}
            className={`relative flex items-center gap-3 px-4 py-3 rounded-2xl text-sm font-medium transition-all duration-300 whitespace-nowrap ${
              isActive ? "text-white shadow-sm" : "text-white/50 hover:text-white hover:bg-white/5"
            }`}
          >
            {isActive && (
              <motion.div
                layoutId="activeNavIndicator"
                className="absolute inset-0 bg-white/10 border border-white/20 rounded-2xl"
                initial={false}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <Icon className={`w-5 h-5 z-10 transition-colors ${isActive ? "text-accent" : "text-white/40"}`} />
            <span className="z-10">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
