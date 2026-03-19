"use client";

import { useEffect, useState } from "react";

import Navbar from "../components/Navbar";
import { authFetch, clearToken, getToken } from "../lib/auth";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const TOPICS = [
  { label: "LLMs", value: "LLMs" },
  { label: "Multimodal Models", value: "Multimodal" },
  { label: "Diffusion Models", value: "Diffusion" },
  { label: "RAG", value: "RAG" },
  { label: "Agents", value: "Agents" },
  { label: "Efficient Training", value: "Efficient Training" },
  { label: "Computer Vision", value: "Computer Vision" },
  { label: "Robotics", value: "Robotics" }
];

export default function OnboardingPage() {
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
    }
  }, []);

  function toggleTopic(topic: string) {
    setSelected((prev) => (prev.includes(topic) ? prev.filter((item) => item !== topic) : [...prev, topic]));
  }

  async function saveTopics() {
    if (selected.length === 0) {
      setError("Select at least one topic to continue");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await authFetch(`${apiBase}/user/topics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topics: selected })
      });
      if (res.status === 401) {
        clearToken();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        throw new Error("Failed to save topics");
      }
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save topics");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto max-w-2xl px-4 py-12">
        <h1 className="text-2xl font-semibold text-slate-900">What research topics are you interested in?</h1>
        <p className="mt-2 text-sm text-slate-500">Pick a few so we can personalize your feed.</p>

        <div className="mt-6 flex flex-wrap gap-3">
          {TOPICS.map((topic) => {
            const active = selected.includes(topic.value);
            return (
              <button
                key={topic.value}
                onClick={() => toggleTopic(topic.value)}
                className={`rounded-full px-4 py-2 text-sm transition ${
                  active ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-700 hover:bg-white"
                }`}
              >
                {topic.label}
              </button>
            );
          })}
        </div>

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

        <button
          onClick={saveTopics}
          disabled={saving}
          className="mt-6 rounded-full bg-[#68B0AB] px-6 py-2 text-sm text-white hover:bg-[#4A7C59]"
        >
          {saving ? "Saving..." : "Continue"}
        </button>
      </div>
    </main>
  );
}
