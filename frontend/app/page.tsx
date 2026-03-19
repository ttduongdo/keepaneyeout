"use client";

import { useEffect, useState } from "react";

import BoardTabs from "./components/BoardTabs";
import Navbar from "./components/Navbar";
import PostFeed from "./components/PostFeed";
import SaveToBoardModal from "./components/SaveToBoardModal";
import TrendDashboard from "./components/TrendDashboard";
import { getToken } from "./lib/auth";
import type { Post } from "./lib/api";
import { fetchBoardPosts } from "./lib/api";
import { useTopics } from "./hooks/useTopics";

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState<"boards" | "trending">("boards");
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null);
  const [saveModalPost, setSaveModalPost] = useState<Post | null>(null);
  const [boardClusters, setBoardClusters] = useState<string[]>([]);
  const [boardPostIds, setBoardPostIds] = useState<string[]>([]);
  const { selectedTopics, clearSelectedTopics } = useTopics();

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
      return;
    }
    if (typeof window !== "undefined") {
      const storedTab = window.sessionStorage.getItem("feed_active_tab");
      const storedBoardId = window.sessionStorage.getItem("feed_active_board_id");
      if (storedTab === "trending" || storedTab === "boards") {
        setActiveTab(storedTab);
      }
      if (storedBoardId) {
        setActiveBoardId(storedBoardId);
      } else if (storedTab === "boards") {
        setActiveBoardId(null);
      }
    }
  }, []);

  useEffect(() => {
    if (!activeBoardId) {
      setBoardClusters([]);
      setBoardPostIds([]);
      return;
    }
    void loadBoardClusters(activeBoardId);
  }, [activeBoardId]);

  async function loadBoardClusters(boardId: string) {
    try {
      const posts = await fetchBoardPosts(boardId);
      const clusters = Array.from(new Set(posts.map((post) => post.topic_cluster).filter(Boolean))) as string[];
      setBoardClusters(clusters);
      setBoardPostIds(posts.map((post) => post.id));
    } catch {
      setBoardClusters([]);
      setBoardPostIds([]);
    }
  }

  function handleNavbarSearch(value: string) {
    setSearchQuery(value);
    window.location.href = `/papers/search?q=${encodeURIComponent(value)}`;
  }

  const selectedClusters = selectedTopics.length > 0 ? selectedTopics : undefined;
  const recommendedClusters = activeBoardId ? boardClusters : selectedClusters;
  const latestClusters = activeBoardId ? undefined : selectedClusters;

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar searchQuery={searchQuery} onSearchChange={setSearchQuery} onSearchSubmit={handleNavbarSearch} />

      <div className="mx-auto w-full max-w-[1500px] space-y-6 px-4 py-6 md:px-8">
        <div className="flex flex-col gap-3">
          <h1 className="text-2xl font-semibold text-slate-900">Discovery Feed</h1>
          <BoardTabs
            activeBoardId={activeBoardId}
            activeTab={activeTab}
            onSelectTrending={() => {
              setActiveTab("trending");
              clearSelectedTopics();
              if (typeof window !== "undefined") {
                window.sessionStorage.setItem("feed_active_tab", "trending");
              }
            }}
            onSelectBoard={(boardId) => {
              setActiveTab("boards");
              setActiveBoardId(boardId);
              clearSelectedTopics();
              if (typeof window !== "undefined") {
                window.sessionStorage.setItem("feed_active_tab", "boards");
                if (boardId) {
                  window.sessionStorage.setItem("feed_active_board_id", boardId);
                } else {
                  window.sessionStorage.removeItem("feed_active_board_id");
                }
              }
            }}
          />
        </div>

        {activeTab === "trending" ? (
          <TrendDashboard />
        ) : (
          <div className="space-y-8">
            {selectedTopics.length > 0 && (
              <div className="flex items-center justify-between rounded-xl bg-white/70 px-4 py-3 text-sm text-slate-700">
                <span>Filtering by: {selectedTopics.join(", ")}</span>
                <button
                  className="rounded-lg bg-white/80 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-white"
                  onClick={clearSelectedTopics}
                >
                  Reset to subscriptions
                </button>
              </div>
            )}
            <PostFeed
              title={activeBoardId ? "Recommended from this board" : "Recommended For You"}
              section="recommended"
              topicClusters={recommendedClusters}
              excludeIds={activeBoardId ? boardPostIds : undefined}
              onSave={(post) => setSaveModalPost(post)}
            />
            <PostFeed
              title="Latest"
              section="latest"
              topicClusters={latestClusters}
              onSave={(post) => setSaveModalPost(post)}
            />
          </div>
        )}
      </div>

      <SaveToBoardModal
        post={saveModalPost}
        isOpen={saveModalPost !== null}
        onClose={() => setSaveModalPost(null)}
      />
    </main>
  );
}
