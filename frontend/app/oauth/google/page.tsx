"use client";

import { useEffect, useState } from "react";

import { authFetch, setToken } from "../../lib/auth";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type AuthResponse = { access_token: string };

type MeResponse = { topics: string[] };

export default function GoogleOAuthPage() {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void exchangeCode();
  }, []);

  async function exchangeCode() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code) {
      setError("Missing OAuth code");
      return;
    }

    try {
      const res = await fetch(`${apiBase}/auth/google/callback?code=${encodeURIComponent(code)}`);
      if (!res.ok) {
        throw new Error("Google OAuth failed");
      }
      const data = (await res.json()) as AuthResponse;
      setToken(data.access_token);
      const meRes = await authFetch(`${apiBase}/me`);
      if (meRes.ok) {
        const me = (await meRes.json()) as MeResponse;
        if (me.topics && me.topics.length > 0) {
          window.location.href = "/";
          return;
        }
      }
      window.location.href = "/onboarding";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google OAuth failed");
    }
  }

  return (
    <main className="min-h-screen bg-transparent flex items-center justify-center">
      <div className="rounded-2xl border border-slate-200 bg-white/90 px-6 py-4 text-sm text-slate-700">
        {error ? error : "Completing Google sign-in..."}
      </div>
    </main>
  );
}
