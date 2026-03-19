"use client";

import { useEffect, useState } from "react";

import Navbar from "../../components/Navbar";
import type { Paper } from "../../components/PaperCard";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type PaperDetail = Paper & {
  abstract: string;
  summary_full: string;
};

type RelatedPaper = Paper;

export default function PaperDetailPage({ params }: { params: { id: string } }) {
  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [related, setRelated] = useState<RelatedPaper[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadPaper();
    void loadRelated();
  }, [params.id]);

  async function loadPaper() {
    try {
      const res = await fetch(`${apiBase}/papers/${params.id}`);
      if (!res.ok) {
        throw new Error(`Paper not found (${res.status})`);
      }
      const data = (await res.json()) as PaperDetail;
      setPaper(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load paper");
    }
  }

  async function loadRelated() {
    try {
      const res = await fetch(`${apiBase}/papers/${params.id}/related`);
      if (!res.ok) {
        return;
      }
      const data = (await res.json()) as RelatedPaper[];
      setRelated(data);
    } catch {
      // ignore
    }
  }

  if (error) {
    return <p className="mx-auto max-w-4xl p-6 text-sm text-red-600">{error}</p>;
  }

  if (!paper) {
    return <p className="mx-auto max-w-4xl p-6 text-sm text-slate-500">Loading...</p>;
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto max-w-4xl px-4 py-8">
        <h1 className="text-3xl font-semibold text-slate-900">{paper.title}</h1>
        <p className="mt-2 text-sm text-slate-500">{Array.isArray(paper.authors) ? paper.authors.join(", ") : paper.authors}</p>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white/90 p-4">
          <h2 className="text-lg font-semibold">TLDR Summary</h2>
          <p className="mt-2 text-sm text-slate-700">{paper.summary_full || paper.summary}</p>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white/90 p-4">
          <h2 className="text-lg font-semibold">Abstract</h2>
          <p className="mt-2 text-sm text-slate-700 whitespace-pre-wrap">{paper.abstract}</p>
        </section>

        <section className="mt-6 rounded-2xl border border-slate-200 bg-white/90 p-4">
          <h2 className="text-lg font-semibold">Related papers</h2>
          {related.length === 0 ? (
            <p className="mt-2 text-sm text-slate-500">No related papers found.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {related.map((item) => (
                <li key={item.id} className="text-sm">
                  <a href={`/papers/${item.id}`} className="underline">
                    {item.title}
                  </a>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}
