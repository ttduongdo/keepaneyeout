"use client";

import { useEffect, useState } from "react";

import type { Board } from "../lib/api";
import { fetchBoards } from "../lib/api";
import { authFetch } from "../lib/auth";

type BoardTabsProps = {
  activeBoardId?: string | null;
  activeTab: "boards" | "trending";
  onSelectBoard: (boardId: string | null) => void;
  onSelectTrending: () => void;
};

export default function BoardTabs({ activeBoardId, activeTab, onSelectBoard, onSelectTrending }: BoardTabsProps) {
  const [boards, setBoards] = useState<Board[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    void loadBoards();
  }, []);

  async function loadBoards() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBoards(authFetch);
      setBoards(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load boards");
    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            activeTab === "trending"
              ? "bg-[#8FC0A9] text-white"
              : "bg-white/70 text-slate-700 hover:bg-white"
          }`}
          onClick={onSelectTrending}
        >
          Trending
        </button>
        <button
          className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
            activeTab === "boards" && !activeBoardId
              ? "bg-[#8FC0A9] text-white"
              : "bg-white/70 text-slate-700 hover:bg-white"
          }`}
          onClick={() => onSelectBoard(null)}
        >
          All
        </button>
        {loading && <span className="text-xs text-slate-400">Loading boards...</span>}
        {!loading &&
          boards.map((board) => (
            <button
              key={board.id}
              className={`rounded-lg px-4 py-2 text-sm font-medium transition ${
                activeTab === "boards" && activeBoardId === board.id
                  ? "bg-[#8FC0A9] text-white"
                  : "bg-white/70 text-slate-700 hover:bg-white"
              }`}
              onClick={() => onSelectBoard(board.id)}
            >
              {board.name}
            </button>
          ))}
      </div>
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
