"use client";

import { useEffect, useState } from "react";

import BoardGrid from "../components/BoardGrid";
import Navbar from "../components/Navbar";
import { authFetch, clearToken, getToken } from "../lib/auth";

type Board = { id: string; name: string };

type BoardDetail = { id: string; name: string; papers: { id: string }[] };

export default function BoardsPage() {
  const [boards, setBoards] = useState<{ id: string; name: string; count?: number }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!getToken()) {
      window.location.href = "/login";
      return;
    }
    void loadBoards();
  }, []);

  async function loadBoards() {
    setError(null);
    try {
      const res = await authFetch("/boards");
      if (res.status === 401) {
        clearToken();
        window.location.href = "/login";
        return;
      }
      if (!res.ok) {
        throw new Error("Failed to load boards");
      }
      const data = (await res.json()) as Board[];
      const withCounts = await Promise.all(
        data.map(async (board) => {
          const detailRes = await authFetch(`/boards/${board.id}`);
          if (!detailRes.ok) {
            return { ...board };
          }
          const detail = (await detailRes.json()) as BoardDetail;
          return { ...board, count: detail.papers.length };
        })
      );
      setBoards(withCounts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load boards");
    }
  }

  return (
    <main className="min-h-screen bg-transparent">
      <Navbar />
      <div className="mx-auto w-full max-w-[1500px] space-y-6 px-4 py-10">
        <h1 className="text-2xl font-semibold text-slate-900">Your boards</h1>
        <BoardGrid boards={boards} />
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </main>
  );
}
