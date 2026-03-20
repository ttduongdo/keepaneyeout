"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import Navbar from "../../components/Navbar";
import PostCard from "../../components/PostCard";
import SaveToBoardModal from "../../components/SaveToBoardModal";
import type { Post, PostFeedResponse } from "../../lib/api";
import Masonry from "react-masonry-css";
import { authFetch } from "../../lib/auth";
import { MASONRY_BREAKPOINTS } from "../../lib/masonry";
import { useTopics } from "../../hooks/useTopics";

export default function PaperSearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Post[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveModalPost, setSaveModalPost] = useState<Post | null>(null);
  const searchParams = useSearchParams();
  const [toast, setToast] = useState<string | null>(null);
  const { subscribedTopics, addSubscribedTopic, removeSubscribedTopic } = useTopics();

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    await runSearch(query);
  }

  async function runSearch(value: string) {
    const trimmed = value.trim();
    if (!trimmed) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await authFetch(`/posts?q=${encodeURIComponent(trimmed)}&page=1&page_size=50`);
      if (!res.ok) {
        throw new Error(`Search failed (${res.status})`);
      }
      const data = (await res.json()) as PostFeedResponse;
      setResults(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const initial = searchParams.get("q") || "";
    if (!initial) {
      return;
    }
    setQuery(initial);
    void runSearch(initial);
  }, [searchParams]);

  const normalizedQuery = useMemo(() => query.trim(), [query]);
  const isSubscribed = normalizedQuery ? subscribedTopics.includes(normalizedQuery) : false;

  async function toggleSubscription() {
    if (!normalizedQuery) {
      return;
    }
    try {
      if (isSubscribed) {
        await removeSubscribedTopic(normalizedQuery);
        setToast(`Unsubscribed from ${normalizedQuery}`);
      } else {
        await addSubscribedTopic(normalizedQuery);
        setToast(`Subscribed to ${normalizedQuery}`);
      }
      window.setTimeout(() => setToast(null), 2500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Subscription failed");
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto w-full max-w-[1500px] px-4 py-6 md:px-8 md:py-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-semibold">
            {query ? `Showing results for “${query}”` : "Showing results"}
          </h1>
          {normalizedQuery && (
            <button
              onClick={toggleSubscription}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                isSubscribed ? "bg-[#8FC0A9] text-white" : "bg-white/70 text-slate-700 hover:bg-white"
              }`}
            >
              {isSubscribed ? "Subscribed" : "Subscribe"}
            </button>
          )}
        </div>

        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
        {toast && <p className="mt-3 text-sm text-emerald-700">{toast}</p>}

        <div className="mt-6">
          {results.length === 0 && !loading && <p className="text-sm text-slate-500">No results found.</p>}
          {results.length > 0 && (
            <Masonry breakpointCols={MASONRY_BREAKPOINTS} className="masonry-grid" columnClassName="masonry-column">
              {results.map((post) => (
                <PostCard key={post.id} post={post} onSave={(item) => setSaveModalPost(item)} />
              ))}
            </Masonry>
          )}
        </div>

        <SaveToBoardModal
          post={saveModalPost}
          isOpen={saveModalPost !== null}
          onClose={() => setSaveModalPost(null)}
        />
      </div>
    </main>
  );
}
