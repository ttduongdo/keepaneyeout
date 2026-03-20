"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import Navbar from "../components/Navbar";
import { authFetch, getToken, setToken } from "../lib/auth";
import { getApiBase } from "../lib/apiBase";

const apiBase = getApiBase();

type AuthResponse = { access_token: string };

type MeResponse = { topics: string[] };

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getToken()) {
      window.location.href = "/";
    }
  }, []);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        throw new Error("Invalid credentials");
      }
      const data = (await res.json()) as AuthResponse;
      setToken(data.access_token);
      const topicsRes = await authFetch("/me");
      if (topicsRes.ok) {
        const me = (await topicsRes.json()) as MeResponse;
        if (me.topics && me.topics.length > 0) {
          window.location.href = "/";
          return;
        }
      }
      window.location.href = "/onboarding";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setError(null);
    try {
      const res = await fetch(`${apiBase}/auth/google/login`);
      if (!res.ok) {
        throw new Error("Google OAuth not available");
      }
      const data = (await res.json()) as { url: string };
      window.location.href = data.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Google login failed");
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Log in</h1>
          <p className="mt-2 text-sm text-slate-500">Access your personalized research feed.</p>
        </div>

        <button
          onClick={handleGoogleLogin}
          className="rounded-full bg-white/70 px-4 py-2 text-sm text-slate-700 hover:bg-white"
        >
          Continue with Google
        </button>

        <form onSubmit={handleLogin} className="space-y-3">
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            className="w-full rounded-full bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]"
            disabled={loading}
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <p className="text-sm text-slate-600">
          New here? <Link href="/signup" className="underline">Create an account</Link>
        </p>
      </div>
    </main>
  );
}
