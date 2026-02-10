"use client";

import { FormEvent, useMemo, useState } from "react";

type SearchResult = {
  chunk_id: string;
  document_id: string;
  title: string;
  url: string;
  source: string;
  published_at: string;
  snippet: string;
  score: number;
};

type Citation = {
  document_id: string;
  title: string;
  url: string;
  chunk_id: string;
  snippet: string;
};

type AskResponse = {
  answer: string;
  citations: Citation[];
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("transformers for long-context reasoning");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [askQuery, setAskQuery] = useState("What are recent directions in LLM efficiency?");
  const [askLoading, setAskLoading] = useState(false);
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const hasSearchResults = useMemo(() => searchResults.length > 0, [searchResults]);

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSearchLoading(true);
    try {
      const res = await fetch(`${apiBase}/search?q=${encodeURIComponent(searchQuery)}&k=10`);
      if (!res.ok) {
        throw new Error(`Search failed (${res.status})`);
      }
      const data = (await res.json()) as SearchResult[];
      setSearchResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearchLoading(false);
    }
  }

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setAskLoading(true);
    try {
      const res = await fetch(`${apiBase}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: askQuery, k: 8 })
      });
      if (!res.ok) {
        throw new Error(`Ask failed (${res.status})`);
      }
      const data = (await res.json()) as AskResponse;
      setAskResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ask failed");
    } finally {
      setAskLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-6 space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold">AI Research Radar</h1>
        <p className="text-sm text-slate-600">Minimal RAG research tracker (arXiv baseline)</p>
      </header>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="text-lg font-medium">Search</h2>
        <form onSubmit={onSearch} className="mt-3 flex gap-2">
          <input
            className="flex-1 rounded border px-3 py-2"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Enter search query"
          />
          <button className="rounded bg-slate-900 px-4 py-2 text-white" disabled={searchLoading}>
            {searchLoading ? "Searching..." : "Search"}
          </button>
        </form>
        {hasSearchResults && (
          <ul className="mt-4 space-y-3">
            {searchResults.map((r) => (
              <li key={r.chunk_id} className="rounded border p-3">
                <a href={r.url} target="_blank" rel="noreferrer" className="font-medium underline">
                  {r.title}
                </a>
                <p className="mt-1 text-sm text-slate-700">{r.snippet}</p>
                <p className="mt-1 text-xs text-slate-500">score: {r.score.toFixed(4)}</p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border bg-white p-4 shadow-sm">
        <h2 className="text-lg font-medium">Ask</h2>
        <form onSubmit={onAsk} className="mt-3 space-y-2">
          <textarea
            className="w-full rounded border px-3 py-2"
            value={askQuery}
            onChange={(e) => setAskQuery(e.target.value)}
            rows={3}
            placeholder="Ask a question"
          />
          <button className="rounded bg-slate-900 px-4 py-2 text-white" disabled={askLoading}>
            {askLoading ? "Asking..." : "Ask"}
          </button>
        </form>

        {askResponse && (
          <div className="mt-4 space-y-3">
            <p className="text-sm leading-6">{askResponse.answer}</p>
            <h3 className="font-medium">Citations</h3>
            <ul className="space-y-2">
              {askResponse.citations.map((c) => (
                <li key={c.chunk_id} className="rounded border p-3 text-sm">
                  <a href={c.url} target="_blank" rel="noreferrer" className="font-medium underline">
                    {c.title}
                  </a>
                  <p className="mt-1 text-slate-700">{c.snippet}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {error && <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </main>
  );
}
