"use client";

import { FormEvent, useEffect, useState } from "react";

type Topic = { id: string; name: string; description: string };

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export default function SubscribePage() {
  const [email, setEmail] = useState("");
  const [frequency, setFrequency] = useState("daily");
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopics, setSelectedTopics] = useState<string[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadTopics();
  }, []);

  async function loadTopics() {
    try {
      const res = await fetch(`${apiBase}/topics`);
      if (!res.ok) {
        return;
      }
      const data = (await res.json()) as Topic[];
      setTopics(data);
    } catch {
      // keep form usable
    }
  }

  function toggleTopic(topicId: string) {
    setSelectedTopics((prev) =>
      prev.includes(topicId) ? prev.filter((id) => id !== topicId) : [...prev, topicId]
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus(null);
    setError(null);

    try {
      const res = await fetch(`${apiBase}/subscriptions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, topic_ids: selectedTopics, frequency })
      });
      if (!res.ok) {
        throw new Error(`Subscribe failed (${res.status})`);
      }
      setStatus("Subscription saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Subscribe failed");
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-6 md:px-8 md:py-10">
      <h1 className="text-3xl font-semibold">Subscribe</h1>
      <p className="mt-2 text-sm text-slate-600">Get daily or weekly AI Research Radar digests by email.</p>

      <form onSubmit={onSubmit} className="mt-4 space-y-4 rounded-2xl border border-slate-300/90 bg-white/70 p-4 backdrop-blur-sm">
        <input
          className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          required
        />

        <select className="w-full rounded-md border border-slate-300 bg-white/80 px-3 py-2 text-sm" value={frequency} onChange={(e) => setFrequency(e.target.value)}>
          <option value="daily">daily</option>
          <option value="weekly">weekly</option>
        </select>

        <div>
          <p className="text-sm font-medium">Topic filters (optional)</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {topics.map((topic) => (
              <label key={topic.id} className="flex items-center gap-2 rounded border border-slate-300 bg-white/70 p-2 text-sm">
                <input type="checkbox" checked={selectedTopics.includes(topic.id)} onChange={() => toggleTopic(topic.id)} />
                <span>{topic.name}</span>
              </label>
            ))}
          </div>
        </div>

        <button className="rounded-md bg-[#68B0AB] px-4 py-2 text-sm text-white hover:bg-[#4A7C59]" type="submit">
          Save subscription
        </button>
      </form>

      {status && <p className="mt-4 rounded border border-emerald-300 bg-emerald-50 p-3 text-sm text-emerald-800">{status}</p>}
      {error && <p className="mt-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
    </main>
  );
}
