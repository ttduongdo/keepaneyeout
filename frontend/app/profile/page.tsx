"use client";

import { useEffect, useMemo, useState } from "react";

import BoardGrid from "../components/BoardGrid";
import Navbar from "../components/Navbar";
import TopicChip from "../components/TopicChip";
import { useTopics } from "../hooks/useTopics";
import { authFetch, clearToken, getToken } from "../lib/auth";

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

type Board = { id: string; name: string };

type BoardDetail = { id: string; name: string; papers: { id: string; title: string; published_date: string }[] };

type MeResponse = { id: string; email: string; topics: string[] };

const TOPIC_SUGGESTIONS = [
  "LLMs",
  "Multimodal Models",
  "Diffusion Models",
  "RAG",
  "Agents",
  "Efficient Training",
  "Computer Vision",
  "Robotics",
  "Evaluation",
  "Inference",
  "Alignment",
  "Safety"
];

export default function ProfilePage() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [boards, setBoards] = useState<Board[]>([]);
  const [papers, setPapers] = useState<BoardDetail["papers"]>([]);
  const [error, setError] = useState<string | null>(null);
  const [topicInput, setTopicInput] = useState("");
  const [toast, setToast] = useState<string | null>(null);
  const { subscribedTopics, addSubscribedTopic, removeSubscribedTopic } = useTopics();

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
      return;
    }
    void loadProfile();
  }, []);

  async function loadProfile() {
    setError(null);
    try {
      const [meRes, boardsRes] = await Promise.all([
        authFetch(`${apiBase}/me`),
        authFetch(`${apiBase}/boards`)
      ]);

      if (meRes.status === 401 || boardsRes.status === 401) {
        clearToken();
        window.location.href = "/login";
        return;
      }

      if (meRes.ok) {
        setMe((await meRes.json()) as MeResponse);
      }
      if (boardsRes.ok) {
        const data = (await boardsRes.json()) as Board[];
        setBoards(data);
        await loadBoardPapers(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    }
  }

  async function loadBoardPapers(items: Board[]) {
    const collected: BoardDetail["papers"] = [];
    for (const board of items) {
      const res = await authFetch(`${apiBase}/boards/${board.id}`);
      if (!res.ok) {
        continue;
      }
      const detail = (await res.json()) as BoardDetail;
      collected.push(...detail.papers);
    }
    setPapers(collected);
  }

  const filteredSuggestions = useMemo(() => {
    const query = topicInput.trim().toLowerCase();
    if (!query) {
      return TOPIC_SUGGESTIONS.filter((topic) => !subscribedTopics.includes(topic));
    }
    return TOPIC_SUGGESTIONS.filter(
      (topic) => topic.toLowerCase().includes(query) && !subscribedTopics.includes(topic)
    );
  }, [topicInput, subscribedTopics]);

  async function handleAddTopic(topic: string) {
    const normalized = topic.trim();
    if (!normalized) {
      return;
    }
    try {
      await addSubscribedTopic(normalized);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Failed to subscribe");
      window.setTimeout(() => setToast(null), 2000);
      return;
    }
    setTopicInput("");
    setToast(`Subscribed to ${normalized}`);
    window.setTimeout(() => setToast(null), 2000);
  }

  async function handleRemoveTopic(topic: string) {
    try {
      await removeSubscribedTopic(topic);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Failed to remove");
      window.setTimeout(() => setToast(null), 2000);
      return;
    }
    setToast(`Removed ${topic}`);
    window.setTimeout(() => setToast(null), 2000);
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto w-full max-w-[1500px] space-y-8 px-4 py-10">
        <section className="rounded-2xl border border-slate-200 bg-white/90 p-6">
          <h1 className="text-2xl font-semibold text-slate-900">Your profile</h1>
          <p className="mt-2 text-sm text-slate-500">{me?.email ?? ""}</p>
        </section>

        <section className="space-y-4 rounded-2xl border border-slate-200 bg-white/90 p-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Subscribed Topics</h2>
            <p className="text-sm text-slate-500">Manage your research focus areas.</p>
          </div>
          {subscribedTopics.length === 0 ? (
            <p className="text-sm text-slate-500">No subscriptions yet.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {subscribedTopics.map((topic) => (
                <TopicChip key={topic} label={topic} onRemove={() => handleRemoveTopic(topic)} />
              ))}
            </div>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700">Add Topic</label>
            <input
              value={topicInput}
              onChange={(event) => setTopicInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  handleAddTopic(topicInput);
                }
              }}
              placeholder="Type a topic and press Enter"
              className="w-full rounded-lg bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 focus:outline-none"
            />
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-semibold text-slate-700">Recommended Topics</h3>
            <div className="flex flex-wrap gap-2">
              {TOPIC_SUGGESTIONS.filter((topic) => !subscribedTopics.includes(topic))
                .slice(0, 8)
                .map((topic) => (
                  <TopicChip key={topic} label={topic} onClick={() => handleAddTopic(topic)} />
                ))}
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Boards</h2>
          <BoardGrid boards={boards} />
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-semibold text-slate-900">Saved papers</h2>
          {papers.length === 0 ? (
            <p className="text-sm text-slate-500">No papers saved yet.</p>
          ) : (
            <ul className="space-y-2">
              {papers.map((paper) => (
                <li key={paper.id} className="rounded-2xl border border-slate-200 bg-white/90 p-4">
                  <a href={`/papers/${paper.id}`} className="text-sm font-semibold text-slate-900">
                    {paper.title}
                  </a>
                  <p className="mt-2 text-xs text-slate-500">Published {new Date(paper.published_date).getFullYear()}</p>
                </li>
              ))}
            </ul>
          )}
        </section>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {toast && <p className="text-sm text-emerald-700">{toast}</p>}
      </div>
    </main>
  );
}
