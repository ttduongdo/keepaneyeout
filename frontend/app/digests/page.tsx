"use client";

import { useEffect, useState } from "react";

type Digest = {
  id: string;
  date: string;
  content_md: string;
  stats: Record<string, unknown>;
  created_at: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function DigestsPage() {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadDigests();
  }, []);

  async function loadDigests() {
    try {
      const res = await fetch(`${apiBase}/digests?limit=30`);
      if (!res.ok) {
        throw new Error(`Failed to load digests (${res.status})`);
      }
      const data = (await res.json()) as Digest[];
      setDigests(data);
      if (data.length > 0) {
        setSelectedDate(data[0].date);
        setSelectedDigest(data[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load digests");
    }
  }

  async function selectDigest(date: string) {
    setSelectedDate(date);
    try {
      const res = await fetch(`${apiBase}/digests/${date}`);
      if (!res.ok) {
        throw new Error(`Failed to load digest (${res.status})`);
      }
      const data = (await res.json()) as Digest;
      setSelectedDigest(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load digest");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
      <h1 className="text-3xl font-semibold">Digests</h1>
      <p className="mt-2 text-sm text-slate-600">Daily newsletter archives.</p>

      <div className="mt-4 grid gap-4 md:grid-cols-[280px_1fr]">
        <aside className="rounded-2xl border border-slate-300/90 bg-white/70 p-4 backdrop-blur-sm">
          <h2 className="text-sm font-medium">Available dates</h2>
          <ul className="mt-2 space-y-2">
            {digests.map((digest) => (
              <li key={digest.id}>
                <button
                  className={`w-full rounded px-3 py-2 text-left text-sm transition ${selectedDate === digest.date ? "bg-[#8FC0A9] text-white" : "bg-white/70 hover:bg-white"}`}
                  onClick={() => selectDigest(digest.date)}
                >
                  {digest.date}
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="rounded-2xl border border-slate-300/90 bg-white/70 p-4 backdrop-blur-sm">
          {selectedDigest ? (
            <pre className="whitespace-pre-wrap text-sm text-slate-800">{selectedDigest.content_md}</pre>
          ) : (
            <p className="text-sm text-slate-600">No digest selected.</p>
          )}
        </section>
      </div>

      {error && <p className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </main>
  );
}
