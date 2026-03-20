"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import Navbar from "../components/Navbar";
import { getToken, setToken } from "../lib/auth";
import { getApiBase } from "../lib/apiBase";

const apiBase = getApiBase();

type AuthResponse = { access_token: string };

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getToken()) {
      window.location.href = "/";
    }
  }, []);

  async function handleSignup(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        throw new Error("Signup failed");
      }
      const data = (await res.json()) as AuthResponse;
      setToken(data.access_token);
      window.location.href = "/onboarding";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto flex max-w-md flex-col gap-6 px-4 py-12">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Create account</h1>
          <p className="mt-2 text-sm text-slate-500">Start tracking the research that matters to you.</p>
        </div>

        <form onSubmit={handleSignup} className="space-y-3">
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
          <input
            className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
            placeholder="Confirm password"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          <button
            className="w-full rounded-full bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]"
            disabled={loading}
          >
            {loading ? "Creating..." : "Sign up"}
          </button>
        </form>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <p className="text-sm text-slate-600">
          Already have an account? <Link href="/login" className="underline">Log in</Link>
        </p>
      </div>
    </main>
  );
}
