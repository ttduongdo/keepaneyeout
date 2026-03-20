"use client";

import { useEffect, useState } from "react";

import { authFetch } from "../lib/auth";

type TrendSummaryResponse = {
  summary_md: string;
};

export default function TrendSummary() {
  const [summary, setSummary] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadSummary();
  }, []);

  async function loadSummary() {
    try {
      const res = await authFetch("/papers/trends");
      if (!res.ok) {
        throw new Error(`Trend summary failed (${res.status})`);
      }
      const data = (await res.json()) as TrendSummaryResponse;
      setSummary(data.summary_md || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trend summary failed");
    }
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-[0_10px_30px_rgba(15,23,42,0.06)]">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">AI Research Trends This Week</h2>
        <span className="text-xs text-slate-500">Updated weekly</span>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!error && !summary && <p className="mt-3 text-sm text-slate-500">Loading trends...</p>}
      {summary && (
        <div className="mt-3 space-y-2 text-sm text-slate-700 whitespace-pre-line">{summary}</div>
      )}
    </section>
  );
}
