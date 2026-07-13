"use client";

import { useState } from "react";
import { Lock } from "lucide-react";

export default function Login() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  const handleLogin = () => {
    if (!token.trim()) {
      setError("Please enter an access token");
      return;
    }
    document.cookie = `mission_control_token=${token}; path=/; max-age=86400; SameSite=Lax`;
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a] p-4">
      <div className="glass-panel p-8 max-w-sm w-full text-center border border-white/10">
        <Lock className="w-12 h-12 text-white/50 mx-auto mb-4" />
        <h1 className="text-xl text-white font-bold mb-2">Mission Control</h1>
        <p className="text-sm text-white/40 mb-6">
          Enter your access token to continue
        </p>
        <input
          type="password"
          placeholder="Access Token"
          value={token}
          onChange={(e) => {
            setToken(e.target.value);
            setError("");
          }}
          className="w-full bg-white/5 border border-white/10 text-white rounded-lg px-4 py-3 mb-3 focus:outline-none focus:border-white/30 transition-colors text-sm"
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          autoFocus
        />
        {error && (
          <p className="text-danger text-xs mb-3 text-left">{error}</p>
        )}
        <button
          onClick={handleLogin}
          className="w-full bg-white text-black font-semibold py-3 rounded-lg hover:bg-white/90 transition-colors text-sm"
        >
          Authenticate
        </button>
      </div>
    </div>
  );
}
