"use client";
import { useState } from "react";
import { Lock } from "lucide-react";

export default function Login() {
  const [token, setToken] = useState("");

  const handleLogin = () => {
    document.cookie = `mission_control_token=${token}; path=/; max-age=86400`;
    window.location.href = "/";
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#050505]">
      <div className="glass-panel p-8 max-w-sm w-full text-center border border-white/10 rounded-xl">
        <Lock className="w-12 h-12 text-white/50 mx-auto mb-4" />
        <h1 className="text-xl text-white font-bold mb-6">Mission Control</h1>
        <input 
          type="password"
          placeholder="Access Token"
          value={token}
          onChange={e => setToken(e.target.value)}
          className="w-full bg-white/5 border border-white/10 text-white rounded p-3 mb-4 focus:outline-none focus:border-white/30"
          onKeyDown={e => e.key === 'Enter' && handleLogin()}
        />
        <button 
          onClick={handleLogin}
          className="w-full bg-white text-black font-bold py-3 rounded hover:bg-white/90 transition-colors"
        >
          Authenticate
        </button>
      </div>
    </div>
  );
}
